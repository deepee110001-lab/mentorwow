-- Event Networking Graph (DPDP-aware). New tables are net_* so existing
-- mentorship tables stay intact. User profile columns are added if missing.

CREATE TABLE IF NOT EXISTS net_profiles (
  id INTEGER PRIMARY KEY,
  user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
  skill_tags TEXT DEFAULT '[]',
  can_advise_on TEXT DEFAULT '[]',
  open_to_collaborate_on TEXT DEFAULT '[]',
  resume_url TEXT,
  resume_visible_default INTEGER DEFAULT 0,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS net_events (
  id INTEGER PRIMARY KEY,
  organizer_id INTEGER NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  join_link_token TEXT UNIQUE NOT NULL,
  starts_at TEXT NOT NULL,
  ends_at TEXT NOT NULL,
  chat_opens_at TEXT NOT NULL,
  chat_closes_at TEXT NOT NULL,
  feed_closes_at TEXT NOT NULL,
  status TEXT DEFAULT 'live',
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS net_event_members (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES net_events(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  joined_at TEXT,
  attendance_visibility TEXT DEFAULT 'visible',
  resume_visible_this_event INTEGER DEFAULT 0,
  accepted_join INTEGER DEFAULT 0,
  show_contact_after_call INTEGER DEFAULT 1,
  UNIQUE(event_id, user_id)
);

CREATE TABLE IF NOT EXISTS net_queries (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES net_events(id),
  author_id INTEGER NOT NULL REFERENCES users(id),
  type TEXT NOT NULL,
  body TEXT NOT NULL,
  available_slots TEXT DEFAULT '[]',
  status TEXT DEFAULT 'open',
  created_at TEXT,
  expires_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_net_queries_event_type_status ON net_queries(event_id, type, status);

CREATE TABLE IF NOT EXISTS net_query_matches (
  id INTEGER PRIMARY KEY,
  query_id INTEGER NOT NULL REFERENCES net_queries(id),
  matched_user_id INTEGER NOT NULL REFERENCES users(id),
  notified_at TEXT,
  response TEXT DEFAULT 'pending',
  responded_at TEXT,
  reason TEXT DEFAULT '',
  UNIQUE(query_id, matched_user_id)
);

CREATE TABLE IF NOT EXISTS net_calls (
  id INTEGER PRIMARY KEY,
  query_id INTEGER REFERENCES net_queries(id),
  requester_id INTEGER NOT NULL REFERENCES users(id),
  responder_id INTEGER NOT NULL REFERENCES users(id),
  scheduled_at TEXT NOT NULL,
  duration_minutes INTEGER DEFAULT 5,
  meeting_url TEXT,
  status TEXT DEFAULT 'scheduled',
  feedback_requester TEXT,
  feedback_responder TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS net_chat_messages (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES net_events(id),
  author_id INTEGER REFERENCES users(id),
  parent_id INTEGER REFERENCES net_chat_messages(id),
  body TEXT NOT NULL,
  is_pinned INTEGER DEFAULT 0,
  is_system INTEGER DEFAULT 0,
  flagged INTEGER DEFAULT 0,
  flag_reason TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS net_audit_log (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  action TEXT NOT NULL,
  target_type TEXT DEFAULT '',
  target_id TEXT DEFAULT '',
  metadata_json TEXT DEFAULT '{}',
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS net_notifications (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  title TEXT NOT NULL,
  body TEXT DEFAULT '',
  link TEXT DEFAULT '',
  read INTEGER DEFAULT 0,
  created_at TEXT
);
