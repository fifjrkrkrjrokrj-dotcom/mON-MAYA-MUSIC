import asyncio
import os
import re
from typing import Union

import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch

from Ayush.utils.formatters import time_to_seconds

# =========================
# NEW API
# =========================
API_URL = "http://161.97.165.196:8000"

# =========================
# GET MEDIA FROM API
# =========================
async def get_media(query: str, video: bool = False):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/media",
                params={
                    "query": query,
                    "video": str(video).lower()
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:

                if response.status != 200:
                    return None

                data = await response.json()
                return data

    except Exception:
        return None


# =========================
# DOWNLOAD SONG
# =========================
async def download_song(query: str) -> str:
    data = await get_media(query, video=False)

    if not data:
        return None

    download_url = (
        data.get("download_url")
        or data.get("url")
        or data.get("media")
    )

    if not download_url:
        return None

    title = data.get("title", "song")
    safe_title = re.sub(r'[\\/:*?"<>|]', "", title)

    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    file_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}.mp3")

    if os.path.exists(file_path):
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                download_url,
                timeout=aiohttp.ClientTimeout(total=600)
            ) as response:

                if response.status != 200:
                    return None

                with open(file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(1024 * 16):
                        f.write(chunk)

        return file_path

    except Exception:
        return None


# =========================
# DOWNLOAD VIDEO
# =========================
async def download_video(query: str) -> str:
    data = await get_media(query, video=True)

    if not data:
        return None

    download_url = (
        data.get("download_url")
        or data.get("url")
        or data.get("media")
    )

    if not download_url:
        return None

    title = data.get("title", "video")
    safe_title = re.sub(r'[\\/:*?"<>|]', "", title)

    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    file_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}.mp4")

    if os.path.exists(file_path):
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                download_url,
                timeout=aiohttp.ClientTimeout(total=1200)
            ) as response:

                if response.status != 200:
                    return None

                with open(file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(1024 * 16):
                        f.write(chunk)

        return file_path

    except Exception:
        return None


# =========================
# SHELL CMD
# =========================
async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    out, errorz = await proc.communicate()

    if errorz:
        if "unavailable videos are hidden" in (
            errorz.decode("utf-8")
        ).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")

    return out.decode("utf-8")


# =========================
# YOUTUBE API CLASS
# =========================
class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
        )

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link

        return bool(re.search(self.regex, link))

    async def url(
        self,
        message_1: Message
    ) -> Union[str, None]:

        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:

            if message.entities:
                for entity in message.entities:

                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption

                        return text[
                            entity.offset:
                            entity.offset + entity.length
                        ]

            elif message.caption_entities:
                for entity in message.caption_entities:

                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url

        return None

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)

        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]

            duration_sec = (
                int(time_to_seconds(duration_min))
                if duration_min else 0
            )

        return (
            title,
            duration_min,
            duration_sec,
            thumbnail,
            vidid
        )

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        try:
            downloaded_file = await download_video(link)

            if downloaded_file:
                return 1, downloaded_file
            else:
                return 0, "Video download failed"

        except Exception as e:
            return 0, f"Video download error: {e}"

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)

        for result in (await results.next())["result"]:

            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]

            thumbnail = (
                result["thumbnails"][0]["url"]
                .split("?")[0]
            )

        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }

        return track_details, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:

        if videoid:
            link = self.base + link

        try:

            if video:
                downloaded_file = await download_video(link)
            else:
                downloaded_file = await download_song(link)

            if downloaded_file:
                return downloaded_file, True

            return None, False

        except Exception:
            return None, False
