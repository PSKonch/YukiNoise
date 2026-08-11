export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface Artist {
  id: string;
  user_id: string;
  displayed_name: string;
  bio: string | null;
  social_links: Record<string, string> | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface Track {
  id: string;
  release_id: string;
  title: string;
  duration_seconds: number;
  track_number_in_release: number;
  genres: string[];
  path: string;
  created_at?: string | null;
  deleted_at?: string | null;
}

export interface Release {
  id: string;
  artist_id: string;
  title: string;
  description: string | null;
  cover_path: string | null;
  release_type: "single" | "ep" | "album";
  status: "draft" | "scheduled" | "published" | "deleted" | string;
  release_date: string | null;
  created_at: string | null;
  updated_at: string | null;
  deleted_at: string | null;
  author_name?: string | null;
  tracks?: Track[];
}

export interface Post {
  id: string;
  artist_id: string;
  title: string;
  content: string;
  author_name: string | null;
  created_at: string | null;
  updated_at: string | null;
  deleted_at: string | null;
}

export interface Commentary {
  id: string;
  artist_id: string;
  post_id: string;
  commentary_id: string | null;
  content: string;
  author_name: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export type LikeTargetType = "track" | "release" | "playlist" | "post" | "commentary";

export interface Playlist {
  id: string;
  artist_id: string;
  title: string;
  description: string | null;
  cover_url: string | null;
  is_private: boolean;
  playlist_type: "system" | "user";
  created_at: string | null;
  updated_at: string | null;
  deleted_at: string | null;
}

export interface PlaylistTrack {
  playlist_id: string;
  track_id: string;
  added_at: string | null;
  track: Track | null;
}

export type ViewName = "discover" | "artists" | "feed" | "library" | "studio" | "settings";
