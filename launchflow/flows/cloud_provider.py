from enum import Enum

import beaupy  # type: ignore
import rich

XML_TEMPLATE = """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <array>
    <dict>
      <key>choiceAttribute</key>
      <string>customLocation</string>
      <key>attributeSetting</key>
      <string>{install_dir}</string>
      <key>choiceIdentifier</key>
      <string>default</string>
    </dict>
  </array>
</plist>
"""


class CloudProvider(Enum):
    GCP = "gcp"
    AWS = "aws"
    AZURE = "azure"


CLOUD_PROVIDER_CHOICES = [
    (CloudProvider.GCP, "Google Cloud Platform"),
    (CloudProvider.AWS, "Amazon Web Services"),
    # (CloudProvider.AZURE, "Microsoft Azure"),
]


def select_cloud_provider() -> CloudProvider:
    options = [f"{f[0].value.upper()} - {f[1]}" for f in CLOUD_PROVIDER_CHOICES]
    answer = beaupy.select(options=options, return_index=True)
    rich.print(f"[pink1]>[/pink1] {options[answer]}")
    return CLOUD_PROVIDER_CHOICES[answer][0]
