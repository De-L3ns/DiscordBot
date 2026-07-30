from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class NostalgiaImageDto:
    title: str
    image_url: str

    def __post_init__(self) -> None:
        parsed_url = urlparse(self.image_url)
        if parsed_url.scheme != "https" or not parsed_url.hostname:
            raise ValueError("image_url must be an absolute HTTPS URL")
