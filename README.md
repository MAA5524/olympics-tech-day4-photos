# Third Technology Olympiad — Day 4 Photo Gallery

An online photo archive of **Day 4 of the 3rd Technology Olympiad**, featuring the **Image Processing and Natural Language Processing (NLP) League**.

This repository provides a responsive photo gallery with optimized WebP images, original image download links, and an automated image-processing and deployment pipeline powered by **GitHub Actions** and **GitHub Pages**.

## 🌐 Online Gallery

**[View the Day 4 Photo Gallery](https://maa5524.github.io/olympics-tech-day4-photos/)**

The gallery provides:

- **Photo Grid:** Browse event photos through a responsive thumbnail gallery.
- **Full-Size Viewer:** Open images in a larger view.
- **Image Navigation:** Move between photos using previous and next controls.
- **Slideshow:** Automatically cycle through the photo collection.
- **Thumbnail Filmstrip:** Navigate quickly between images.
- **Image Information:** View the original filename and file size.
- **Download Original:** Download the original high-resolution image directly from UUpload.

## ✨ Features

### Automated Image Processing

The project uses Python and Pillow to process images automatically:

- Extracts direct image download links from a UUpload public folder.
- Identifies duplicate image links and avoids processing mirrored copies.
- Downloads original images temporarily during the build process.
- Converts images into the WebP format.
- Generates optimized thumbnails for the gallery grid.
- Generates larger optimized images for the full-size viewer.
- Creates a JSON manifest containing image metadata and source URLs.
- Removes temporary original image files after processing.

### Automated Deployment

GitHub Actions handles the entire build and deployment pipeline:

1. Retrieves the repository source code.
2. Sets up the Python environment.
3. Installs the required dependencies.
4. Extracts and downloads images from UUpload.
5. Generates optimized WebP images and the photo manifest.
6. Uploads the generated website as a GitHub Pages artifact.
7. Deploys the gallery to GitHub Pages.

No local image downloading or manual deployment is required.

## 🏗️ Architecture

The project uses a simple static-site architecture.

```text
UUpload
   |
   | Original Images
   v
GitHub Actions
   |
   |-- Extract Image URLs
   |
   |-- Download Original Images
   |
   |-- Optimize with Pillow
   |
   |-- Generate WebP Images
   |
   |-- Generate photos.json
   |
   v
Generated Website (dist/)
   |
   |-- index.html
   |-- assets/
   |-- media/
       |-- large/
       |-- thumbs/
       |-- photos.json
   |
   v
GitHub Pages
   |
   v
Online Photo Gallery
```

Original high-resolution images remain hosted on UUpload. Only optimized WebP images and the website assets are included in the generated GitHub Pages deployment.

## 📁 Repository Structure

```text
olympics-tech-day4-photos/
│
├── .github/
│   └── workflows/
│       └── build-gallery.yml
│
├── assets/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── gallery.js
│
├── scripts/
│   ├── build_gallery.py
│   └── requirements.txt
│
├── .gitignore
├── .nojekyll
├── index.html
├── LICENSE
└── README.md
```

### Generated Deployment Structure

The following directory is generated automatically by GitHub Actions during each build. It does not need to be maintained manually.

```text
dist/
│
├── index.html
│
├── assets/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── gallery.js
│
└── media/
    ├── large/
    │   ├── 00001.webp
    │   ├── 00002.webp
    │   └── ...
    │
    ├── thumbs/
    │   ├── 00001.webp
    │   ├── 00002.webp
    │   └── ...
    │
    └── photos.json
```

### Directory Overview

| Path | Description |
|---|---|
| `.github/workflows/` | GitHub Actions automation workflows |
| `assets/css/` | Gallery styles and responsive layout |
| `assets/js/` | Gallery functionality and interactions |
| `scripts/` | Python image-processing utilities |
| `scripts/build_gallery.py` | Main image extraction and optimization script |
| `scripts/requirements.txt` | Python dependencies |
| `index.html` | Main gallery page |
| `dist/` | Generated static website and optimized images |
| `media/large/` | Optimized images for the full-size viewer |
| `media/thumbs/` | Optimized thumbnails for the gallery grid |
| `media/photos.json` | Image manifest containing metadata and download URLs |

## 🚀 Getting Started

### Prerequisites

- A GitHub account.
- A public GitHub repository.
- GitHub Actions enabled.
- GitHub Pages configured to use GitHub Actions.
- A publicly accessible UUpload folder containing the original images.

### 1. Clone the Repository

```bash
git clone https://github.com/MAA5524/olympics-tech-day4-photos.git

cd olympics-tech-day4-photos
```

### 2. Install Python Dependencies

Python 3.12 is used in the GitHub Actions workflow.

Install the required packages:

```bash
python3 -m pip install -r scripts/requirements.txt
```

### 3. Run the Gallery Locally

Set the source UUpload folder URL:

**Linux / macOS:**

```bash
export UU_PAGE_URL="https://my.uupload.ir/f/amirmofatehi/ax%20day4"
```

**Windows PowerShell:**

```powershell
$env:UU_PAGE_URL="https://my.uupload.ir/f/amirmofatehi/ax%20day4"
```

Run the image-processing script:

```bash
python scripts/build_gallery.py
```

The generated website will be available inside the `dist/` directory.

Start a local HTTP server:

```bash
python3 -m http.server 8000 --directory dist
```

Open:

```text
http://localhost:8000
```

## ⚙️ GitHub Actions Workflow

The project uses GitHub Actions to automate image processing and website deployment.

Workflow file:

```text
.github/workflows/build-gallery.yml
```

### Manual Execution

The workflow is triggered manually using `workflow_dispatch`.

To run it:

1. Open the repository's **Actions** tab.
2. Select **Build and Deploy Photo Gallery**.
3. Click **Run workflow**.
4. Enter the public UUpload folder URL.
5. Start the workflow.

The workflow uses the supplied URL as its image source.

### Build Process

The `build` job performs the following operations:

| Step | Description |
|---|---|
| Checkout | Retrieves the repository source code |
| Setup Python | Configures Python 3.12 |
| Install Dependencies | Installs the required Python packages |
| Build Photo Gallery | Extracts, downloads and optimizes images |
| Configure Pages | Prepares GitHub Pages deployment |
| Upload Pages Artifact | Uploads the generated `dist/` directory |

### Deployment Process

After the build job succeeds, the `deploy` job publishes the generated artifact using the official GitHub Pages deployment action.

The deployment process does not require manually uploading generated files to the repository.

## 🖼️ Image Processing

The project generates two optimized versions of each original image.

| Image Version | Maximum Dimension | WebP Quality | Purpose |
|---|---:|---:|---|
| Thumbnail | 400 px | 75 | Gallery grid |
| Large | 1600 px | 82 | Full-size viewer |

Images are converted to WebP using Pillow.

### Photo Manifest

The generated `media/photos.json` file contains the metadata required by the frontend.

Example:

```json
{
  "filename": "DSC00001.jpg",
  "size": "19.18 MB",
  "size_bytes": 20111687,
  "download_url": "https://example.uupload.ir/files/DSC00001.jpg?download",
  "thumb": "media/thumbs/00001.webp",
  "large": "media/large/00001.webp"
}
```

Each entry contains:

| Field | Description |
|---|---|
| `filename` | Original image filename |
| `size` | Human-readable original file size |
| `size_bytes` | Original file size in bytes |
| `download_url` | Direct download URL for the original image |
| `thumb` | Relative path to the optimized thumbnail |
| `large` | Relative path to the larger optimized image |

The frontend reads this manifest to populate the gallery and manage image navigation.

## 📥 Downloading Original Images

The gallery provides access to the original high-resolution images.

To download an original image:

1. Open the online gallery.
2. Select the desired photo.
3. Open the full-size viewer.
4. Click the **Download Original** button.

The original image is retrieved directly from its UUpload hosting URL rather than from the optimized WebP version.

## 🌍 Deployment

The project uses **GitHub Pages with GitHub Actions**.

To configure deployment:

1. Open the repository's **Settings**.
2. Navigate to **Pages**.
3. Under **Build and deployment**, select `GitHub Actions` as the source.

After a successful workflow execution, the website is published at:

```text
https://maa5524.github.io/olympics-tech-day4-photos/
```

The generated `dist/` directory is used as the deployment artifact.

## 📊 Technology Stack

| Technology | Purpose |
|---|---|
| HTML5 | Gallery structure |
| CSS3 | Responsive styling and layout |
| JavaScript | Gallery interactions and image navigation |
| Python 3.12 | Image extraction and processing |
| Pillow | Image resizing and WebP conversion |
| Requests | HTTP requests and image downloads |
| BeautifulSoup4 | HTML parsing and URL extraction |
| tqdm | Processing progress display |
| GitHub Actions | Automated build pipeline |
| GitHub Pages | Static website hosting |
| UUpload | Original image hosting |

## 📄 License

This repository includes an MIT License for the software components.

The license of the software does not automatically grant rights to redistribute event photographs. Please respect the photographers' rights, event policies, and applicable permissions when downloading or sharing images.

## 🙌 Credits

- Original gallery implementation adapted from [FunCodingLab](https://github.com/FunCodingLab/olympics-tech-day2-photos).
- Image processing and automated deployment pipeline maintained in this repository.
- Original event photographs hosted on [UUpload](https://my.uupload.ir/).

A digital archive of Day 4 of the 3rd Technology Olympiad — Image Processing and NLP League.

---

*Preserving moments, people, and memories from the Technology Olympiad.*
