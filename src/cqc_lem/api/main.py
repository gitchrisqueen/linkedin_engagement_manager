import time
from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel, computed_field

from cqc_lem.utilities.db import get_db_connection

app = FastAPI()


class PostType(str, Enum):
    text = "text"
    carousel = "carousel"
    video = "video"


class PostRequest(BaseModel):
    content: str
    post_type: Optional[PostType] = PostType.text
    scheduled_datetime: datetime

    @property
    def post_json(self):
        json = self.model_dump()
        json['scheduled_datetime'] = self.scheduled_time
        return json

    @computed_field
    @property
    def scheduled_time(self) -> str:
        # Add Timezone to scheduled_datetime
        time.tzset()
        return self.scheduled_datetime.isoformat()


@app.post("/schedule_post/")
def schedule_post(post: PostRequest):
    """Endpoint to schedule a post."""

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO posts (content, scheduled_time, post_type) VALUES (%s, %s, %s)",
        (post.content, post.scheduled_time, post.post_type)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "Post scheduled successfully"}


@app.get("/posts/")
def get_posts(
        #user_id: None
):
    """Endpoint to get all posts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id =  None
    where_clause = ""
    if user_id is not None:
        where_clause = "WHERE user_id = " + user_id
    cursor.execute(
        f"SELECT id, content, scheduled_time, post_type FROM posts {where_clause} ORDER BY scheduled_time asc"
    )

    posts = cursor.fetchall()
    cursor.close()
    conn.close()

    # Convert posts to a list of dictionaries
    posts_list = [{"post_id": post[0], "content": post[1], "scheduled_time": post[2], "post_type": post[3]} for post in posts]

    return {"status": "Success", 'data': posts_list}


@app.post("/update_post/")
def update_post(post_id: int, post: PostRequest):
    """Endpoint to update a post."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE posts SET content = %s, scheduled_time = %s, post_type = %s WHERE id = %s",
        (post.content, post.scheduled_time, post.post_type, post_id)
    )
    if cursor.rowcount == 0:
        #raise HTTPException(status_code=404, detail="Post not found")
        return {"status": f"Post ID: {post_id} Not Foud"}
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "Post updated successfully"}
