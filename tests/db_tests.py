from datetime import datetime

from cqc_lem.utilities.db import update_db_post_status, PostStatus, update_db_post_video_url, update_db_post_content


def test_change_post_status():
    post_id = 19
    api_video_url = "https://cqc-lem-api.ngrok-free.dev/assets?file_name=videos/runwayml/fd06a3e2-8d38-435e-a172-1be0429fee5c.mp4"
    update_db_post_video_url(post_id, api_video_url)
    today_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_db_post_content(post_id, f"This is a test post. {today_date}")
    update_db_post_status(post_id, PostStatus.PENDING)


if __name__ == "__main__":
    test_change_post_status()
