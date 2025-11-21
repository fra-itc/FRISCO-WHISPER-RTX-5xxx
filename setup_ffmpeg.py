#!/usr/bin/env python3
"""
FFmpeg Setup Script - Download and configure ffmpeg locally for the project

This script automatically downloads and extracts the appropriate ffmpeg binaries
for the current platform, placing them in the project's bin/ directory.

Supports:
- Linux (x64, arm64)
- Windows (x64)
- macOS (x64, arm64)

Usage:
    python setup_ffmpeg.py
    python setup_ffmpeg.py --force  # Force re-download even if exists
"""

import os
import sys
import platform
import urllib.request
import tarfile
import zipfile
import shutil
from pathlib import Path
import hashlib


class FFmpegSetup:
    """Download and configure ffmpeg binaries for local project use."""

    # FFmpeg download URLs (latest static builds)
    FFMPEG_URLS = {
        'linux_x64': {
            'url': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz',
            'type': 'tar.xz'
        },
        'linux_arm64': {
            'url': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz',
            'type': 'tar.xz'
        },
        'windows_x64': {
            'url': 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
            'type': 'zip'
        },
        'darwin_x64': {
            'url': 'https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip',
            'type': 'zip'
        },
        'darwin_arm64': {
            'url': 'https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip',
            'type': 'zip'
        }
    }

    def __init__(self, project_root: Path = None):
        """
        Initialize FFmpeg setup.

        Args:
            project_root: Root directory of the project (default: script location)
        """
        self.project_root = project_root or Path(__file__).parent
        self.bin_dir = self.project_root / 'bin'
        self.download_dir = self.project_root / 'downloads'
        self.platform_key = self._detect_platform()

    def _detect_platform(self) -> str:
        """
        Detect current platform and architecture.

        Returns:
            Platform key (e.g., 'linux_x64', 'windows_x64')
        """
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Normalize architecture names
        if machine in ('x86_64', 'amd64'):
            arch = 'x64'
        elif machine in ('aarch64', 'arm64'):
            arch = 'arm64'
        else:
            arch = 'x64'  # Default fallback

        platform_key = f"{system}_{arch}"

        if platform_key not in self.FFMPEG_URLS:
            raise RuntimeError(
                f"Unsupported platform: {platform_key}\n"
                f"Supported: {', '.join(self.FFMPEG_URLS.keys())}"
            )

        return platform_key

    def is_installed(self) -> bool:
        """
        Check if ffmpeg is already installed locally.

        Returns:
            True if ffmpeg and ffprobe binaries exist
        """
        ffmpeg_path = self.bin_dir / ('ffmpeg.exe' if 'windows' in self.platform_key else 'ffmpeg')
        ffprobe_path = self.bin_dir / ('ffprobe.exe' if 'windows' in self.platform_key else 'ffprobe')

        return ffmpeg_path.exists() and ffprobe_path.exists()

    def get_binary_paths(self) -> dict:
        """
        Get paths to ffmpeg and ffprobe binaries.

        Returns:
            Dict with 'ffmpeg' and 'ffprobe' paths
        """
        ext = '.exe' if 'windows' in self.platform_key else ''
        return {
            'ffmpeg': str(self.bin_dir / f'ffmpeg{ext}'),
            'ffprobe': str(self.bin_dir / f'ffprobe{ext}')
        }

    def download_ffmpeg(self, force: bool = False) -> bool:
        """
        Download ffmpeg for current platform.

        Args:
            force: Force download even if already exists

        Returns:
            True if download successful
        """
        if self.is_installed() and not force:
            print(f"✅ FFmpeg already installed in {self.bin_dir}")
            return True

        # Create directories
        self.bin_dir.mkdir(exist_ok=True)
        self.download_dir.mkdir(exist_ok=True)

        # Get platform-specific URL
        config = self.FFMPEG_URLS[self.platform_key]
        url = config['url']
        file_type = config['type']

        # Determine download filename
        filename = url.split('/')[-1]
        download_path = self.download_dir / filename

        print(f"🔽 Downloading ffmpeg for {self.platform_key}...")
        print(f"   URL: {url}")

        try:
            # Download with progress
            self._download_with_progress(url, download_path)

            print(f"\n📦 Extracting ffmpeg...")

            # Extract based on file type
            if file_type == 'tar.xz':
                self._extract_tar_xz(download_path)
            elif file_type == 'zip':
                self._extract_zip(download_path)

            # Verify installation
            if self.is_installed():
                print(f"✅ FFmpeg installed successfully!")
                self._print_binary_info()

                # Cleanup download
                if download_path.exists():
                    download_path.unlink()

                return True
            else:
                print(f"❌ Installation verification failed")
                return False

        except Exception as e:
            print(f"❌ Error downloading ffmpeg: {e}")
            return False

    def _download_with_progress(self, url: str, dest: Path):
        """Download file with progress bar."""
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(downloaded * 100 / total_size, 100)
                bar_length = 40
                filled = int(bar_length * percent / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f'\r   [{bar}] {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)', end='')

        urllib.request.urlretrieve(url, dest, progress_hook)

    def _extract_tar_xz(self, archive_path: Path):
        """Extract tar.xz archive and copy binaries."""
        import lzma

        # Extract to temporary directory
        extract_dir = self.download_dir / 'ffmpeg_extracted'
        extract_dir.mkdir(exist_ok=True)

        with lzma.open(archive_path, 'rb') as xz_file:
            with tarfile.open(fileobj=xz_file) as tar:
                tar.extractall(extract_dir)

        # Find ffmpeg and ffprobe binaries
        for item in extract_dir.rglob('*'):
            if item.name in ('ffmpeg', 'ffprobe'):
                dest = self.bin_dir / item.name
                shutil.copy2(item, dest)
                dest.chmod(0o755)  # Make executable
                print(f"   ✓ Copied {item.name} to {dest}")

        # Cleanup
        shutil.rmtree(extract_dir)

    def _extract_zip(self, archive_path: Path):
        """Extract zip archive and copy binaries."""
        extract_dir = self.download_dir / 'ffmpeg_extracted'
        extract_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Find ffmpeg and ffprobe binaries
        search_names = ['ffmpeg.exe', 'ffprobe.exe'] if 'windows' in self.platform_key else ['ffmpeg', 'ffprobe']

        for item in extract_dir.rglob('*'):
            if item.name in search_names:
                dest = self.bin_dir / item.name
                shutil.copy2(item, dest)
                if 'windows' not in self.platform_key:
                    dest.chmod(0o755)  # Make executable
                print(f"   ✓ Copied {item.name} to {dest}")

        # Cleanup
        shutil.rmtree(extract_dir)

    def _print_binary_info(self):
        """Print information about installed binaries."""
        paths = self.get_binary_paths()

        print(f"\n📍 Binary locations:")
        for name, path in paths.items():
            size = Path(path).stat().st_size / (1024 * 1024)
            print(f"   {name}: {path} ({size:.1f} MB)")

    def verify_installation(self) -> bool:
        """
        Verify ffmpeg installation by running version command.

        Returns:
            True if ffmpeg works correctly
        """
        if not self.is_installed():
            print("❌ FFmpeg not installed")
            return False

        import subprocess

        paths = self.get_binary_paths()

        print("\n🔍 Verifying installation...")

        for name, path in paths.items():
            try:
                result = subprocess.run(
                    [path, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    # Extract version from output
                    version_line = result.stdout.split('\n')[0]
                    print(f"   ✅ {name}: {version_line}")
                else:
                    print(f"   ❌ {name}: Failed to run")
                    return False

            except Exception as e:
                print(f"   ❌ {name}: Error - {e}")
                return False

        return True

    def cleanup_downloads(self):
        """Remove downloaded archives."""
        if self.download_dir.exists():
            for file in self.download_dir.glob('*'):
                if file.is_file():
                    file.unlink()
                    print(f"🗑️  Removed {file.name}")


def main():
    """Main entry point for setup script."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Download and setup ffmpeg for local project use'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download even if ffmpeg exists'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Only verify existing installation'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Remove downloaded archives'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("FFmpeg Setup for FRISCO WHISPER RTX 5xxx")
    print("=" * 70)

    setup = FFmpegSetup()

    print(f"\n🖥️  Platform: {setup.platform_key}")
    print(f"📂 Project root: {setup.project_root}")
    print(f"📂 Binary directory: {setup.bin_dir}")

    # Verify only
    if args.verify:
        if setup.verify_installation():
            print("\n✅ FFmpeg is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ FFmpeg verification failed")
            sys.exit(1)

    # Cleanup
    if args.cleanup:
        setup.cleanup_downloads()
        sys.exit(0)

    # Download and install
    success = setup.download_ffmpeg(force=args.force)

    if success:
        # Verify
        if setup.verify_installation():
            print("\n" + "=" * 70)
            print("✅ SUCCESS - FFmpeg is ready to use!")
            print("=" * 70)
            print("\nNext steps:")
            print("1. Run your application normally")
            print("2. AudioProcessor will automatically use local ffmpeg")
            print("3. Test with: python -c \"from src.core.audio_processor import AudioProcessor; print('✅ OK' if AudioProcessor()._ffmpeg_available else '❌ FAIL')\"")
            sys.exit(0)
        else:
            print("\n❌ Installation verification failed")
            sys.exit(1)
    else:
        print("\n❌ FFmpeg setup failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
