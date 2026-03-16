create table if not exists subscribers (
  id bigint generated always as identity primary key,
  email text unique not null,
  created_at timestamptz default now()
);
