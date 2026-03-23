"""
artifact_writer.py

Creates and manages run artifact folders and file writes for the MTS pipeline.
All pipeline artifacts must be written through this module to ensure consistent
folder structure and naming across every run.

Run artifacts are stored at:
  <ARTIFACTS_BASE_PATH>/<FEATURE_NAME>/<run_id>/<artifact_name>
"""

import datetime
from pathlib import Path

from src.config import ARTIFACTS_BASE_PATH, FEATURE_NAME


class ArtifactWriter:
    """
    Manages the artifact folder for a single pipeline run.

    Responsibilities:
    - Generate a unique, timestamp-based run ID
    - Create the run directory and any subdirectories
    - Write text artifacts (markdown, JSON) to the run folder
    - Write binary artifacts (images) to an images/ subfolder

    Each instance represents exactly one run.
    """

    def __init__(self, run_id: str | None = None) -> None:
        """
        Initialize the writer and create the run directory.

        Args:
            run_id: Optional explicit run ID. If omitted, a timestamp-based
                    ID is generated (format: YYYYMMDD_HHMMSS).
        """
        # Generate a unique run ID if not provided
        self.run_id: str = run_id or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Build the full path: .agent/evals/runs/<feature>/<run_id>/
        self.run_path: Path = ARTIFACTS_BASE_PATH / FEATURE_NAME / self.run_id

        # Create the directory and all missing parents
        self.run_path.mkdir(parents=True, exist_ok=True)

    def write(self, filename: str, content: str) -> Path:
        """
        Write a text artifact (markdown or JSON) to the run folder.

        Args:
            filename: Artifact filename (e.g., "compacted-source.md").
            content: Full text content to write.

        Returns:
            Absolute Path where the artifact was written.

        Raises:
            IOError: If the file cannot be written to disk.
        """
        artifact_path = self.run_path / filename
        artifact_path.write_text(content, encoding="utf-8")
        return artifact_path

    def write_image(self, filename: str, image_bytes: bytes) -> Path:
        """
        Write a binary image artifact to the run folder's images/ subfolder.

        Used to preserve diagrams and figures extracted from source PDFs.

        Args:
            filename: Image filename (e.g., "q3_diagram.png").
            image_bytes: Raw image bytes to write.

        Returns:
            Absolute Path where the image was written.
        """
        # Keep images in a dedicated subfolder to avoid cluttering run root
        images_dir = self.run_path / "images"
        images_dir.mkdir(exist_ok=True)

        image_path = images_dir / filename
        image_path.write_bytes(image_bytes)
        return image_path

    def artifact_path(self, filename: str) -> Path:
        """
        Return the full path for a named artifact without writing it.

        Useful for passing expected artifact paths to downstream steps.

        Args:
            filename: The artifact filename.

        Returns:
            Full Path for the artifact in this run's folder.
        """
        return self.run_path / filename

    def bin_path(self, filename: str) -> Path:
        """
        Return the full path for a binary artifact in the run's bin/ subfolder.

        The bin/ directory is created on first call. Use this for compiled or
        rendered binary outputs (e.g., PDFs) to keep them separate from text
        artifacts in the run root.

        Args:
            filename: Binary artifact filename (e.g., "compacted-source.pdf").

        Returns:
            Full Path inside <run_path>/bin/.
        """
        bin_dir = self.run_path / "bin"
        bin_dir.mkdir(exist_ok=True)
        return bin_dir / filename
