-- 복지혜택 매칭 웹앱 — Supabase(Postgres) 사용자 데이터 스키마
-- Supabase 대시보드 → SQL Editor 에 붙여넣고 실행하세요.
--
-- 모든 테이블은 RLS(Row Level Security)로 보호됩니다:
-- 로그인한 사용자는 "자신의 행(user_id = 본인)"만 조회·수정·삭제할 수 있습니다.
-- auth.users 는 Supabase Auth가 관리하는 사용자 테이블입니다(구글 로그인 시 자동 생성).

-- =====================================================================
-- 1) 프로필 — 로그인 시 검색 폼 자동완성용
-- =====================================================================
create table if not exists public.profiles (
  user_id     uuid primary key references auth.users(id) on delete cascade,
  age         int,
  ctpv        text,          -- 시/도
  sgg         text,          -- 시/군/구
  themes      text[] default '{}',   -- 관심주제 이름 배열
  households  text[] default '{}',   -- 가구상황 이름 배열
  updated_at  timestamptz default now()
);

alter table public.profiles enable row level security;

create policy "본인 프로필 조회" on public.profiles
  for select using (auth.uid() = user_id);
create policy "본인 프로필 삽입" on public.profiles
  for insert with check (auth.uid() = user_id);
create policy "본인 프로필 수정" on public.profiles
  for update using (auth.uid() = user_id);

-- =====================================================================
-- 2) 북마크 — 관심 혜택 저장
-- =====================================================================
create table if not exists public.bookmarks (
  user_id    uuid not null references auth.users(id) on delete cascade,
  serv_id    text not null,
  serv_nm    text,
  scope      text,           -- 'national' | 'local'
  jur        text,           -- 소관 부처/지자체
  region     text,           -- 지역(지자체인 경우)
  created_at timestamptz default now(),
  primary key (user_id, serv_id)
);

alter table public.bookmarks enable row level security;

create policy "본인 북마크 접근" on public.bookmarks
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- =====================================================================
-- 3) 기록 — 조회 이력 + 신청함 여부
-- =====================================================================
create table if not exists public.history (
  user_id    uuid not null references auth.users(id) on delete cascade,
  serv_id    text not null,
  serv_nm    text,
  scope      text,
  applied    boolean default false,   -- 사용자가 '신청함'으로 표시
  viewed_at  timestamptz default now(),
  primary key (user_id, serv_id)
);

alter table public.history enable row level security;

create policy "본인 기록 접근" on public.history
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
