from sqlalchemy.orm import Session

from .guru import parse_topics
from .models import Follow, Post, Project, User, Vote
from .schemas import MeOut, PostOut, ProjectOut, PublicProfile


def project_out(item: Project) -> ProjectOut:
    return ProjectOut(
        id=item.id,
        title=item.title,
        summary=item.summary,
        url=item.url,
        topics=parse_topics(item.topics),
    )


def me_out(user: User) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        handle=user.handle,
        name=user.name or "",
        headline=user.headline or "",
        photo_url=user.photo_url or "",
        accent=user.accent,
        guru_balance=user.guru_balance,
        projects=[project_out(item) for item in user.projects],
    )


def public_out(user: User, db: Session, viewer_id: int | None) -> PublicProfile:
    topics: list[str] = []
    for item in user.projects:
        topics.extend(parse_topics(item.topics))
    following = False
    if viewer_id:
        following = (
            db.query(Follow)
            .filter(Follow.follower_id == viewer_id, Follow.followee_id == user.id)
            .first()
            is not None
        )
    return PublicProfile(
        handle=user.handle,
        accent=user.accent,
        projects=[project_out(item) for item in user.projects],
        topics=list(dict.fromkeys(topics)),
        following=following,
    )


def post_out(item: Post, db: Session, viewer_id: int | None) -> PostOut:
    vote = 0
    if viewer_id:
        row = db.query(Vote).filter(Vote.user_id == viewer_id, Vote.post_id == item.id).first()
        vote = row.value if row else 0
    return PostOut(
        id=item.id,
        kind=item.kind,
        title=item.title,
        body=item.body,
        topic=item.topic,
        score=item.score,
        created_at=item.created_at,
        handle=item.author.handle,
        accent=item.author.accent,
        my_vote=vote,
    )
