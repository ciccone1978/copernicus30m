# Copernicus DEM Downloader

A user-friendly desktop application for visually selecting and downloading Copernicus GLO-30 Digital Elevation Model (DEM) tiles from AWS Open Data.

This tool provides an interactive map interface, removing the need for users to manually find geographic coordinates. It is designed for GIS professionals, researchers, students, and hobbyists who need easy access to high-quality global elevation data.

![Application Screenshot](https://i.imgur.com/your-screenshot-url.png)
*(Recommendation: Take a screenshot of your application and upload it to a site like Imgur, then replace this link with your own)*

## Features

*   **Interactive Map Interface:** Pan and zoom a global map (powered by OpenStreetMap) to find your area of interest.
*   **Visual Tile Grid:** A 1x1 degree grid overlays the map, showing the exact boundaries of the downloadable DEM tiles.
*   **Click to Select:** Simply click on the grid cells to select or deselect the tiles you need.
*   **Live Coordinate Display:** A status bar provides real-time feedback on mouse coordinates and the current map zoom level.
*   **Sidebar Tile List:** See a clear, formatted list of all the tiles you have selected.
*   **Smart Download Manager:**
    *   Handles downloads in a background thread to keep the application responsive.
    *   Detects if files already exist and asks the user whether to **Overwrite** or **Skip** them.
    *   Provides a size-based progress bar for accurate, smooth progress tracking.
    *   Allows downloads to be **cancelled** mid-process.
*   **Built-in Logging:** Configurable logging for easy debugging and monitoring.

## Installation

This application is built with Python and the Qt (PySide6) framework. It is recommended to run it within a Python virtual environment to manage dependencies.

### Prerequisites

*   **Python 3.9+** installed on your system.
*   **Git** (for cloning the repository).
*   An internet connection for downloading packages and DEM tiles.
*   (Linux Only) You may need to install Qt6 system libraries. On Debian/Ubuntu, this can be done with:
    ```bash
    sudo apt-get install qt6-base-dev
    ```
    On Fedora, this can be done with:
    ```bash
    sudo dnf install qt6-qtbase-devel
    ```

### Setup Instructions

1.  **Clone the Repository:**
    Open your terminal and clone this project to your local machine.
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Create and Activate a Virtual Environment:**
    From the project's root directory, create a virtual environment. The standard name for this is `.venv`.
    
    *   **On Linux/macOS:**
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```
    *   **On Windows:**
        ```bash
        python -m venv .venv
        .venv\Scripts\activate
        ```
    You will know the environment is active when you see `(.venv)` at the beginning of your terminal prompt.

3.  **Install Required Packages:**
    Use `pip` to install all the necessary Python packages from the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

With the `.venv` virtual environment active, simply run the main Python script:

```bash
python copernicus30m.py

# Application Guide

The application will launch in a maximized window.

## Usage

- Use your mouse to pan and zoom the map to your area of interest.  
- Use the **"View" → "Show/Hide Grid"** menu option (or the toolbar button) to toggle the tile grid.  
- Click on any grid cell to select a tile. The tile will be highlighted in blue, and its name will appear in the sidebar list.  
- Click a selected tile again to deselect it.  
- Once you have selected all the desired tiles, click the **"Download Selected Tiles"** button in the sidebar.  
- A dialog will ask you to choose a directory to save the files.  
- If any of the selected tiles already exist in that directory, another dialog will ask for your preference (**Overwrite** or **Skip**).  
- The download will begin, with progress shown in the progress bar. You can click **"Stop Download"** at any time to cancel.  

---

## Future Improvements

This application provides a solid foundation that can be extended with more powerful features. Potential future improvements include:

### Tier 1: User Experience & Polish
- **Clear Selection Button**: A one-click button to deselect all tiles.  
- **Sidebar Tile Count**: A label showing the current number of selected tiles.  
- **Persistent Window State**: Save and restore the window size, position, and splitter state between sessions using `QSettings`.  
- **"About" Dialog**: A standard "About" dialog providing application and data source information.  

### Tier 2: Core Functionality Enhancements
- **Search by Location (Geocoding)**: A search bar to instantly jump to a specific place name (e.g., *"Mount Everest"*).  
- **Display Tile Name on Hover**: Show the name of the tile currently under the mouse cursor in the status bar for zero-click identification.  
- **Export/Import Selection**: Save a list of selected tiles to a file and load it back later to support reproducible workflows.  

### Tier 3: Advanced GIS Features
- **Post-Download Processing**: Integrate GDAL/Rasterio to offer options for merging all downloaded tiles into a single seamless raster or clipping the result to a user-drawn area.  
- **Load AOI from Vector File**: Allow users to load a Shapefile or GeoJSON file, display its outline on the map, and automatically select all intersecting DEM tiles.  

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
