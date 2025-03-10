# Github Contrib Art

**Github Contrib Art** is python script allows you to use your Github Contribution Activity graph as a billboard of artistic self-expression. Each pixel’s grayscale intensity can be mapped to a specific number of commits, allowing you to create patterns or designs in your GitHub contribution graph.

### How to Use

1. **Clone this Repository**: Clone the repository to your local machine.

```bash
git clone <url>
```

2. **Create a New GitHub Repository**: Instead of forking, create a brand-new repo in your GitHub account.

3. **Change the Remote**: Point your local clone to the new repository:

```bash
cd <local-folder>
git remote remove origin
git remote add origin <new-repo-url>
```

4. **Check Out the `develop` Branch**:

```bash
git checkout develop
```

5. **Run the Script**: Install dependencies and execute the script:

```bash
pip install -r requirements.txt
python contrib-art.py --string="HELLO WORLD"
```

If you wish to modify the art, note that deleting the repository entirely and re-pushing the `main` branch is necessary. Simply removing the `main` branch alone will not remove previous commits from the contribution graph.

### Features

- **Flexible Canvas**: The canvas expands horizontally to fit the rendered text or an image. Each column represents a week, and each row represents a day (Sunday through Saturday).
- **Text Rendering**: Render text using a built-in 5×7 pixel font, or specify a custom WOFF font (`--bdfFont`).
- **Image Input**: Supply an image, which is resized and converted into a matrix of commit counts determined by the image’s grayscale intensity.
- **Grayscale-to-Commit Mapping**: Grayscale values (inverted) map to varying commit levels:
  - Level 1: 1–4 commits
  - Level 2: 5–8 commits
  - Level 3: 9–12 commits
  - Level 4: 13–16 commits

### Operating Modes

1. **Test Mode (`--test`)**: Outputs a textual matrix of commit counts to the console, generates a `preview.png`, and provides information such as start/end dates and total commits. No commits are pushed.
2. **Live Mode (Default)**: Checks out the designated tag in `contrib-art.py`, resets the `main` branch to that tag, creates commits for each pixel (based on the intensity), and force-pushes the changes to your fork.

### Command-Line Options

- `--string="TEXT"`: Render a specified text string.
- `--image="path/to/image.png"`: Render an image.
- `--bdfFont="https://github.com/olikraus/u8g2/raw/refs/heads/master/tools/font/bdf/6x10.bdf"`: Specify a custom WOFF font.
- `--startMonth=1` and `--startYear=2025`: Define the starting date for commits.
- `--test`: Enable test mode.

### Example Usage

```bash
# Test mode with a text string
python contrib-art.py --string="HELLO" --startMonth=1 --startYear=2025 --test

# Test mode with a custom WOFF font
python contrib-art.py --string="HELLO" --fontUrl="https://example.com/myfont.woff" --startMonth=1 --startYear=2025 --test

# Test mode with a 7px-tall image
python contrib-art.py --image="my7pxImage.png" --startMonth=1 --startYear=2025 --test

# Live mode
python contrib-art.py --string="HELLO" --startMonth=1 --startYear=2025
```

## License

[MIT](http://opensource.org/licenses/MIT) © [Joshua Bellamy](http://www.psidox.com)
