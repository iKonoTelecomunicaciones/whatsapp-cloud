import asyncio
import os
import tempfile
from logging import Logger, getLogger
from typing import cast

from mautrix.util.formatter import EntityType, MarkdownString
from mautrix.util.formatter import MatrixParser as BaseMatrixParser


async def matrix_to_whatsapp(html: str) -> str:
    parsed = await MatrixParser().parse(html)
    return parsed.text


class WhatsAppFormatString(MarkdownString):
    def format(self, entity_type: EntityType, **kwargs) -> "WhatsAppFormatString":
        prefix = suffix = ""
        if entity_type == EntityType.BOLD:
            prefix = suffix = "*"
        elif entity_type == EntityType.ITALIC:
            prefix = suffix = "_"
        elif entity_type == EntityType.STRIKETHROUGH:
            prefix = suffix = "~"
        elif entity_type == EntityType.URL:
            if kwargs["url"] != self.text:
                suffix = f" ({kwargs['url']})"
        elif entity_type in (EntityType.PREFORMATTED, EntityType.INLINE_CODE):
            prefix = suffix = "```"
        elif entity_type == EntityType.BLOCKQUOTE:
            children = self.trim().split("\n")
            children = [child.prepend("> ") for child in children]
            return self.join(children, "\n")
        elif entity_type == EntityType.HEADER:
            prefix = "#" * kwargs["size"] + " "
        else:
            return self

        self.text = f"{prefix}{self.text}{suffix}"
        return self


class MatrixParser(BaseMatrixParser[WhatsAppFormatString]):
    fs = WhatsAppFormatString

    async def parse(self, data: str) -> WhatsAppFormatString:
        return cast(WhatsAppFormatString, await super().parse(data))


class WhatsappFormatMedia:
    """
    Class to convert multimedia files to standard formats for WhatsApp compatibility.
    - Images (not JPG, JPEG, PNG) -> JPEG
    - Audio (not MP3, MP4, MPEG, AAC, AMR) -> MP3
    - Video (not MP4) -> MP4
    - Other formats like documents stay unchanged
    """

    log: Logger = getLogger("WhatsappFormatMedia")

    # Supported image formats that don't need conversion
    SUPPORTED_IMAGE_FORMATS = {"image/jpeg", "image/jpg", "image/png"}
    # Supported audio formats that don't need conversion
    SUPPORTED_AUDIO_FORMATS = {"audio/mp4", "audio/mpeg", "audio/mp3", "audio/aac", "audio/amr"}
    # Supported video formats that don't need conversion
    SUPPORTED_VIDEO_FORMATS = {"video/mp4"}

    @classmethod
    async def process_media(cls, content: bytes, content_type: str) -> tuple[bytes, str]:
        """
        Process media content and convert to standard format if needed.

        Args:
            content: The media file content as bytes
            content_type: The MIME type of the media file

        Returns:
            tuple of (converted_content, new_content_type)
        """
        # If content type is already in supported format, return as-is
        if (
            content_type in cls.SUPPORTED_IMAGE_FORMATS
            or content_type in cls.SUPPORTED_AUDIO_FORMATS
            or content_type in cls.SUPPORTED_VIDEO_FORMATS
        ):
            return content, content_type

        cls.log.debug(f"Converting media of type {content_type}...")

        # Determine conversion type based on content type
        if content_type.startswith("image/"):
            return await cls._convert_image_to_jpg(content, content_type)
        elif content_type.startswith("audio/"):
            return await cls._convert_audio_to_mp3(content, content_type)
        elif content_type.startswith("video/"):
            return await cls._convert_video_to_mp4(content, content_type)

        cls.log.error(f"Unsupported media type {content_type}, returning original...")
        return content, content_type

    @classmethod
    async def _convert_image_to_jpg(cls, content: bytes, content_type: str) -> tuple[bytes, str]:
        """Convert image to JPG format using FFmpeg."""
        return await cls._run_ffmpeg_conversion(
            content,
            content_type,
            "jpg",
            "image/jpeg",
            ["-vcodec", "mjpeg", "-q:v", "2", "-pix_fmt", "yuvj420p"],
        )

    @classmethod
    async def _convert_audio_to_mp3(cls, content: bytes, content_type: str) -> tuple[bytes, str]:
        """Convert audio to MP3 format using FFmpeg."""
        return await cls._run_ffmpeg_conversion(
            content,
            content_type,
            "mp3",
            "audio/mpeg",
            ["-f", "mp3", "-acodec", "libmp3lame", "-ar", "44100", "-ac", "2", "-b:a", "192k"],
        )

    @classmethod
    async def _convert_video_to_mp4(cls, content: bytes, content_type: str) -> tuple[bytes, str]:
        """Convert video to MP4 format using FFmpeg."""
        return await cls._run_ffmpeg_conversion(
            content,
            content_type,
            "mp4",
            "video/mp4",
            ["-vcodec", "libx264", "-acodec", "aac", "-preset", "medium", "-crf", "23"],
        )

    @classmethod
    async def _run_ffmpeg_conversion(
        cls,
        content: bytes,
        input_content_type: str,
        output_extension: str,
        output_content_type: str,
        ffmpeg_args: list,
    ) -> tuple[bytes, str]:
        """
        Run FFmpeg conversion on the media content.

        Parameters
        ----------
        content: Media content as bytes
        input_content_type: Original content type
        output_extension: Desired output file extension
        output_content_type: Desired output content type
        ffmpeg_args: List of FFmpeg arguments for conversion

        Returns
        -------
        tuple of (converted_content, new_content_type)
        """

        # Create temporary files for input and output
        cls.log.debug(
            f"Running FFmpeg conversion to convert {input_content_type} "
            f"to {output_content_type}..."
        )
        with tempfile.NamedTemporaryFile(delete=False) as input_file:
            input_file.write(content)
            input_path = input_file.name

        output_path = f"{input_path}_output.{output_extension}"

        try:
            # Build FFmpeg command
            cmd = ["ffmpeg", "-i", input_path, "-y"] + ffmpeg_args + [output_path]

            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            await process.communicate()

            if process.returncode != 0:
                # If conversion fails, return original content
                return content, input_content_type

            # Read converted file
            with open(output_path, "rb") as f:
                converted_content = f.read()

            cls.log.debug(
                f"FFmpeg conversion successful: {input_content_type} to {output_content_type}"
            )
            return converted_content, output_content_type

        except Exception as e:
            cls.log.error(f"Error during media conversion: {e}")
            # If any error occurs, return original content
            return content, input_content_type
        finally:
            # Clean up temporary files
            try:
                os.unlink(input_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)
            except OSError:
                pass
