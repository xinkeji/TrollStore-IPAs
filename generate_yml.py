import argparse
import json
import os
from io import StringIO

import mistletoe
import pandas as pd
from bs4 import BeautifulSoup
from github import Github

from get_bundle_id import get_single_bundle_id

def transform_object(original_object):
    transformed_object = {**original_object, "apps": []}

    app_map = {}

    for app in original_object["apps"]:
        # 确保每个关键字段都有合理的默认值
        name = app.get("name", "Unknown")
        bundle_identifier = app.get("bundleIdentifier", "unknown.bundle.identifier")
        version = app.get("version", "1.0")
        version_date = app.get("versionDate", "1970-01-01")
        size = app.get("size", 0)
        download_url = app.get("downloadURL", "")
        developer_name = app.get("developerName", "Unknown Developer")
        localized_description = app.get("localizedDescription", "")
        icon_url = app.get("iconURL", "")

        if name not in app_map:
            app_map[name] = {
                "name": name,
                "bundleIdentifier": bundle_identifier,
                "developerName": developer_name,
                "iconURL": icon_url,
                "versions": [],
            }

        app_map[name]["versions"].append({
            "version": version,
            "date": version_date,
            "size": size,
            "downloadURL": download_url,
            "localizedDescription": localized_description,
        })

    for _, app_info in app_map.items():
        app_info["versions"].sort(key=lambda x: x["date"], reverse=True)

    transformed_object["apps"] = list(app_map.values())

    return transformed_object

def main(token):
    with open("apps.json", "r") as f:
        data = json.load(f)

    if os.path.exists("bundleId.csv"):
        df = pd.read_csv("bundleId.csv")
    else:
        df = pd.DataFrame(columns=["name", "bundleId"])

    md_df = None
    if os.path.exists("README.md"):
        with open("README.md", "r", encoding="utf-8") as f:
            raw_md = f.read()
        html = mistletoe.markdown(raw_md)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if tables:
            md_df = pd.read_html(StringIO(str(tables[1])), keep_default_na=False)[0]
            md_df["App Name"] = md_df["App Name"].str.replace(" ", "").str.lower()

    data["apps"] = []

    g = Github(token)
    repo = g.get_repo("swaggyP36000/TrollStore-IPAs")
    releases = repo.get_releases()

    for release in releases:
        print(release.title)

        for asset in release.get_assets():
            if not asset.name.endswith(".ipa"):
                continue

            name_split = asset.name[:-4].split("-")
            app_name = "-".join(name_split[:-1]) if len(name_split) > 1 else name_split[0]
            version = name_split[-1] if len(name_split) > 1 else "1.0"

            if app_name in df.name.values:
                bundle_id = str(df[df.name == app_name].bundleId.values[0])
            else:
                bundle_id = get_single_bundle_id(asset.browser_download_url)
                df = pd.concat([df, pd.DataFrame({"name": [app_name], "bundleId": [bundle_id]})], ignore_index=True)

            dev_name = ""
            desc = ""
            if md_df is not None:
                row = md_df.loc[md_df["App Name"] == app_name.replace(" ", "").lower()]
                if not row.empty:
                    raw_desc = row["Description"].values[0]
                    raw_last_updated = row["Last Updated"].values[0]
                    raw_status = row["Status"].values[0]
                    desc = f"{raw_desc}\nLast updated: {raw_last_updated}\nStatus: {raw_status}"
                    dev_name = row['Source/Maintainer'].values[0]

            data["apps"].append({
                "name": app_name,
                "iconURL": f"https://cdn.jsdelivr.net/gh/xinkeji/TrollStore-IPAs@main/icons/{bundle_id}.png",
                "downloadURL": asset.browser_download_url,
                "developerName": dev_name,
                
            })

    df.to_csv("bundleId.csv", index=False)

    with open("apps_esign.json", "w") as json_file:
        json.dump(data, json_file, indent=2)

    with open("apps.json", "w") as file:
        json.dump(transform_object(data), file, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--token", help="Github token")
    args = parser.parse_args()

    main(args.token)
