#!/usr/bin/env python3
import argparse
import os
import sys
import re
import subprocess
from datetime import datetime, timedelta, timezone
import requests
from PIL import Image, ImageDraw
from bdflib import reader

BASE_TAG = "v1.2.3"

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--string", type=str, default="", help="Text to render")
  parser.add_argument("--image", type=str, default=None, help="Path to image file")
  parser.add_argument("--bdfFont", type=str, default="https://github.com/olikraus/u8g2/raw/refs/heads/master/tools/font/bdf/6x10.bdf",
            help="Path or URL to a BDF font")
  parser.add_argument("--letterSpacing", type=int, default=0, help="Letter spacing")
  parser.add_argument("--startMonth", type=int, default=None, help="Start month (number)")
  parser.add_argument("--startYear", type=int, default=None, help="Start year (number)")
  parser.add_argument("--test", action="store_true", help="Activate test mode")
  return parser.parse_args()

def commitsForIntensity(measuredIntensity):
  if measuredIntensity == 0:
    return 0
  else:
    return int(round((measuredIntensity / 255) * 16))

def formatBranchName(dt: datetime) -> str:
  months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
  month = months[dt.month - 1]
  day = str(dt.day).zfill(2)
  year = dt.year
  hours = str(dt.hour).zfill(2)
  minutes = str(dt.minute).zfill(2)
  seconds = str(dt.second).zfill(2)
  return f"art-{month}-{day}-{year}-{hours}{minutes}{seconds}"

def getGitFormattedDate(d: datetime) -> str:
  return d.strftime("%a %b %d 00:00 %Y +0000")


def getFormattedDate(d: datetime) -> str:
  return d.strftime("%b %d %Y")

def getStartDate(year: int, month: int) -> datetime:
  d = datetime(year, month, 1, tzinfo=timezone.utc)
  while d.weekday() != 6:
    d += timedelta(days=1)
  return d

def report_warning(lineno: int, message: str) -> None:
  print(f"Problem on line {lineno}: {message}")

def loadBDFFont(bdfFontPath: str):
  localFontPath = bdfFontPath
  if bdfFontPath.startswith("http"):
    res = requests.get(bdfFontPath)
    if res.status_code != 200:
      raise Exception("Failed to download BDF font from " + bdfFontPath)
    fontData = res.text
    localFontPath = os.path.join(os.path.dirname(__file__), "temp_font.bdf")
    with open(localFontPath, "w", encoding="utf-8") as f:
      f.write(fontData)
  with open(localFontPath, "rb") as f:
    font = reader.read_bdf(f, report_warning)
  return font

def render_glyph(glyph, target_height=7):
  width = glyph.bbX if glyph.bbX else glyph.bbW
  if not glyph.data:
    return [[0] * width for _ in range(target_height)]
  bitmap = []
  for row_val in reversed(glyph.data):
    row_str = f"{row_val:0{width}b}"
    bitmap.append([0 if char == "0" else 1 for char in row_str])    
  return bitmap

def renderTextToMatrixBDF(text: str, bdfFontPath: str, letterSpacing: int = 0, spaceSpacing: int = 4):
  font = loadBDFFont(bdfFontPath)
  columns = []
  for ch in text:
    glyph = font.get(ord(ch))
    if glyph is None:
      for _ in range(spaceSpacing + letterSpacing):
        columns.append([0] * 7)
      continue
    bmp = render_glyph(glyph, target_height=7)
    width = len(bmp[0])
    for x in range(width):
      col = []
      for y in range(7):
        col.append(16 if (bmp[y + 1][x] >= 1) else 0)
      columns.append(col)
    for _ in range(letterSpacing):
      columns.append([0] * 7)
  numCols = len(columns)
  rowsArr = []
  for r in range(7):
    row = []
    for c in range(numCols):
      row.append(columns[c][r])
    rowsArr.append(row)
  return rowsArr

def renderImageToMatrix(imagePath: str):
  from PIL import Image
  try:
    img = Image.open(imagePath).convert("RGB")
  except Exception as e:
    raise Exception("Error opening image: " + str(e))
  targetHeight = 7
  finalWidth = round(img.width * (targetHeight / img.height))
  img = img.resize((finalWidth, targetHeight), Image.Resampling.BICUBIC)
  matrix = []
  for y in range(targetHeight):
    row = []
    for x in range(finalWidth):
      r, g, b = img.getpixel((x, y))
      commitCount = commitsForIntensity(r)
      row.append(commitCount)
    matrix.append(row)
  return matrix


def renderMatrixToCanvas(matrix):
  from PIL import Image, ImageDraw
  rows = len(matrix)
  cols = len(matrix[0])
  img = Image.new("RGB", (cols, rows))
  draw = ImageDraw.Draw(img)
  for y in range(rows):
    for x in range(cols):
      count = matrix[y][x] or 0
      gray = 255 - round((count / 16) * 255)
      draw.point((x, y), fill=(gray, gray, gray))
  return img

def hexDigitForCommit(commitNumber: int) -> str:
  return hex(commitNumber)[2:].upper()

def finalAsciiForIntensity(commitCount: int) -> str:
  if commitCount <= 4:
    return '·'
  if commitCount <= 8:
    return '•'
  if commitCount <= 12:
    return '*'
  return '#'

def generateReadmeSection(branchName: str, stats: dict, artGridCurrent) -> str:
  gridStr = "\n".join("".join(row) for row in artGridCurrent)
  return (f"<!-- git-art-section-start -->\n"
      f"# {branchName}\n\n"
      f"Statistics:\n"
      f"- Start / End Date: {stats['dateStart']} / {stats['dateEnd']}\n"
      f"- Current Date: {stats['dateCurrent']}\n"
      f"- Columns: {stats['colsCurrent']} / {stats['colsTotal']}\n"
      f"- Rows: {stats['rowsCurrent']} / {stats['rowsTotal']}\n"
      f"- Pixels: {stats['onPixelCurrent'] + stats['offPixelCurrent']} / {stats['pixelsTotal']}\n"
      f"- On Pixels: {stats['onPixelCurrent']} / {stats['onPixelTotal']}\n"
      f"- Off Pixels: {stats['offPixelCurrent']} / {stats['offPixelTotal']}\n"
      f"- Commits: {stats['commitsCurrent']} / {stats['commitsTotal']}\n\n"
      "```\n" +
      gridStr + "\n"
      "```\n"
      "<!-- git-art-section-end -->\n")

def updateReadme(branchName: str, stats: dict, artGridCurrent):
  startMarker = "<!-- git-art-section-start -->"
  endMarker = "<!-- git-art-section-end -->\n"
  newSection = generateReadmeSection(branchName, stats, artGridCurrent)
  readme_path = "README.md"
  original = ""
  if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
      original = f.read()
  if startMarker in original and endMarker in original:
    regex = re.compile(f"{startMarker}[\\s\\S]*?{endMarker}")
    updated = regex.sub(newSection, original)
  else:
    updated = original + "\n\n" + newSection
  with open(readme_path, "w", encoding="utf-8") as f:
    f.write(updated)

def updateConsoleStatus(branchName: str, stats: dict, artGridCurrent) -> int:
  section = generateReadmeSection(branchName, stats, artGridCurrent)
  lines = section.split("\n")
  numLines = len(lines)
  if stats['commitsCurrent'] == 0:
    sys.stdout.write(section)
  else:
    sys.stdout.write(f"\x1b[{numLines-1}A\x1b[0G")
    sys.stdout.write(section)
  sys.stdout.flush()
  return numLines

def main():
  args = parse_args()

  today = datetime.now(timezone.utc)
  defaultStartYear = today.year - 1
  defaultStartMonth = today.month + 1

  startMonth = args.startMonth if args.startMonth is not None else defaultStartMonth
  startYear = args.startYear if args.startYear is not None else defaultStartYear

  letterSpacing = args.letterSpacing
  inputString = args.string
  imagePath = args.image
  bdfFontPath = args.bdfFont

  matrix = None
  if imagePath:
    try:
      matrix = renderImageToMatrix(imagePath)
    except Exception as err:
      print("Error loading image:", err)
      sys.exit(1)
  elif inputString:
    if bdfFontPath:
      try:
        matrix = renderTextToMatrixBDF(inputString, bdfFontPath, letterSpacing)
      except Exception as err:
        print("Error rendering text using BDF font:", err)
        sys.exit(1)
    else:
      print("For text rendering, please provide a BDF font via the --bdfFont parameter.")
      sys.exit(1)
  else:
    print("Either --string or --image parameter must be provided.")
    sys.exit(1)

  rows = 7
  cols = len(matrix[0])
  onPixelCurrent = 0
  onPixelTotal = 0
  commitsTotal = 0
  offPixelCurrent = 0
  pixelsTotal = rows * cols

  for y in range(rows):
    for x in range(cols):
      count = matrix[y][x] or 0
      if count > 0:
        onPixelTotal += 1
      commitsTotal += count
  offPixelTotal = pixelsTotal - onPixelTotal

  startDate = getStartDate(startYear, startMonth)
  endDate = startDate + timedelta(days=(cols * 7 - 1))
  dateStart = getFormattedDate(startDate)
  dateEnd = getFormattedDate(endDate)

  stats = {
    "dateStart": dateStart,
    "dateEnd": dateEnd,
    "dateCurrent": "",
    "colsCurrent": 0,
    "colsTotal": cols,
    "rowsCurrent": 0,
    "rowsTotal": rows,
    "pixelsTotal": pixelsTotal,
    "onPixelTotal": onPixelTotal,
    "onPixelCurrent": 0,
    "offPixelTotal": offPixelTotal,
    "offPixelCurrent": 0,
    "commitsCurrent": 0,
    "commitsTotal": commitsTotal
  }

  if args.test:
    artGridFinal = []
    for row in matrix:
      artRow = []
      for cell in row:
        artRow.append(finalAsciiForIntensity(cell) if cell > 0 else " ")
      artGridFinal.append(artRow)
    section = generateReadmeSection("git-art-test", stats, artGridFinal)
    print(section)
    previewImg = renderMatrixToCanvas(matrix)
    outPngPath = os.path.join(os.getcwd(), "preview.png")
    previewImg.save(outPngPath)
    print("\nPreview PNG saved to:", outPngPath)
  else:
    try:
      subprocess.run(["git", "checkout", "develop"], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as err:
      print("Error checking out tag", BASE_TAG, ":", err)
      sys.exit(1)

    branchTemp = formatBranchName(datetime.now())
    try:
      subprocess.run(["git", "checkout", "-b", branchTemp], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as err:
      print("Error creating temporary branch:", err)
      sys.exit(1)

    try:
      subprocess.run(["git", "branch", "-D", "main"], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as err:
      pass

    try:
      subprocess.run(["git", "branch", "-m", "main"], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as err:
      print("Error renaming branch to 'main':", err)
      sys.exit(1)

    branchName = "main"
    artGridCurrent = [[" " for _ in range(cols)] for _ in range(7)]
   
    currentsCommit = 0
    updateConsoleStatus(branchName, stats, artGridCurrent)
    for col in range(cols):
      for row in range(7):
        pixelCommits = matrix[row][col] or 0
        if pixelCommits == 0:
          offPixelCurrent += 1
          continue
        onPixelCurrent += 1
        commitDate = startDate + timedelta(days=(col * 7 + row))
        for i in range(pixelCommits):
          if i < pixelCommits - 1:
            newChar = hexDigitForCommit(i + 1)
          else:
            newChar = finalAsciiForIntensity(pixelCommits)
          artGridCurrent[row][col] = newChar
          stats.update({
            "commitsCurrent": currentsCommit + 1,
            "dateCurrent": getGitFormattedDate(commitDate),
            "colsCurrent": col,
            "rowsCurrent": row,
            "onPixelCurrent": onPixelCurrent,
            "offPixelCurrent": offPixelCurrent
          })
          updateReadme(branchName, stats, artGridCurrent)
          updateConsoleStatus(branchName, stats, artGridCurrent)
          try:
            formattedDate = getGitFormattedDate(commitDate)
            subprocess.run(["git", "add", "README.md"], check=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            commitMsg = f"Update pixel at (col:{col}, row:{row}), commit {i+1}/{pixelCommits}"
            subprocess.run(["git", "commit", "-m", commitMsg, "--date", formattedDate],
                     check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
          except Exception as err:
            print("\nError committing update", err)
            sys.exit(1)
          currentsCommit += 1
          print(f"\rProgress: {currentsCommit}/{stats['commitsTotal']} commits done.", end="", flush=True)
    print("")
    print(f"Live mode complete. Branch '{branchName}' created with art commits.")
    try:
      subprocess.run(["git", "push", "origin", "main", "--force"], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as err:
      print("Error pushing main to origin", err)
      sys.exit(1)

if __name__ == "__main__":
  try:
    main()
  except Exception as err:
    print("An error occurred:", err)
    sys.exit(1)
