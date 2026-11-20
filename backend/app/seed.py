from sqlalchemy.orm import Session

from .guru import credit, join_topics
from .models import Follow, Post, Project, User, Vote
from .security import hash_password
from .seed_graph import seed_graph

PEOPLE = [
    {
        "email": "copper.loom@mentorwow.app",
        "handle": "copper-loom",
        "accent": "#3D4A23",
        "guru": 80,
        "projects": [
            {
                "title": "Ledger that forgets names",
                "summary": "A settlement log that stores only handles and hashes. Used it to prove a dispute without doxxing a rider.",
                "url": "https://example.com/ledger",
                "topics": ["product strategy", "privacy"],
            },
            {
                "title": "Queue for five-minute desks",
                "summary": "Matching two chairs on a topic without a calendar. The interesting part was killing the leftover waiters.",
                "url": "",
                "topics": ["product strategy", "system design"],
            },
        ],
    },
    {
        "email": "salt.harbor@mentorwow.app",
        "handle": "salt-harbor",
        "accent": "#5B6B32",
        "guru": 64,
        "projects": [
            {
                "title": "Staff doc people actually read",
                "summary": "A design-doc template that forces tradeoffs above the fold. Shipped it through three orgs.",
                "url": "https://example.com/doc",
                "topics": ["staff engineering", "system design"],
            }
        ],
    },
    {
        "email": "nimbus.kiln@mentorwow.app",
        "handle": "nimbus-kiln",
        "accent": "#2C3619",
        "guru": 41,
        "projects": [
            {
                "title": "Type ramp for a noisy brand",
                "summary": "A system with four sizes and one rule for shouting. Replaced a 60-token mess.",
                "url": "",
                "topics": ["design systems", "brand"],
            }
        ],
    },
    {
        "email": "amber.ridge@mentorwow.app",
        "handle": "amber-ridge",
        "accent": "#445022",
        "guru": 55,
        "projects": [
            {
                "title": "From lab notes to a hiring packet",
                "summary": "Turned a methods appendix into three stories a hiring manager could repeat.",
                "url": "",
                "topics": ["career", "research"],
            }
        ],
    },
]


POSTS = [
    ("copper-loom", "post", "Kill the eight-bet roadmap", "If your board has eight bets, you do not have a board. You have a wish list. I sit on product strategy for five minutes and we pick the three that can die.", "product strategy"),
    ("salt-harbor", "post", "Draw the diagram out loud", "Staff loops fail when the tradeoff stays in your head. I will make you talk while you draw. System design only.", "system design"),
    ("nimbus-kiln", "post", "A type system is a no", "Most design systems are permission structures pretending to be tokens. Happy to sit on that fight.", "design systems"),
    ("amber-ridge", "update", "", "A five-minute session closed on career. No names. The quality room kept the score.", "career"),
    ("copper-loom", "post", "Privacy is a product choice", "If your ledger stores a legal name you did not need, you already lost. Looking for chairs on privacy.", "privacy"),
]


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        seed_graph(db)
        return

    password = hash_password("mentorwow")
    by_handle: dict[str, User] = {}
    for person in PEOPLE:
        user = User(
            email=person["email"],
            hashed_password=password,
            handle=person["handle"],
            accent=person["accent"],
            guru_balance=0,
        )
        db.add(user)
        db.flush()
        credit(db, user, person["guru"], "seed", "opening stack")
        for project in person["projects"]:
            db.add(
                Project(
                    user_id=user.id,
                    title=project["title"],
                    summary=project["summary"],
                    url=project["url"],
                    topics=join_topics(project["topics"]),
                )
            )
        by_handle[user.handle] = user

    db.add_all(
        [
            Follow(follower_id=by_handle["copper-loom"].id, followee_id=by_handle["salt-harbor"].id),
            Follow(follower_id=by_handle["copper-loom"].id, followee_id=by_handle["nimbus-kiln"].id),
            Follow(follower_id=by_handle["salt-harbor"].id, followee_id=by_handle["copper-loom"].id),
            Follow(follower_id=by_handle["amber-ridge"].id, followee_id=by_handle["copper-loom"].id),
        ]
    )

    posts: list[Post] = []
    for handle, kind, title, body, topic in POSTS:
        post = Post(
            author_id=by_handle[handle].id,
            kind=kind,
            title=title,
            body=body,
            topic=topic,
            score=3 if kind == "post" else 1,
        )
        db.add(post)
        db.flush()
        posts.append(post)

    db.add(Vote(user_id=by_handle["salt-harbor"].id, post_id=posts[0].id, value=1))
    db.add(Vote(user_id=by_handle["nimbus-kiln"].id, post_id=posts[0].id, value=1))
    db.commit()
    seed_graph(db)
