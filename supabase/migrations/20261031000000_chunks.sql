-- PolicyDrift demo store: versioned policy chunks with 768-dim e5-base embeddings.
-- Experiments do NOT use this table; they search the local chunk file (docs/retrieval.md).

create extension if not exists vector with schema extensions;

create table if not exists public.chunks (
    chunk_id          text primary key,
    scheme            text        not null,
    version           text        not null,
    effective_from    date,
    effective_to      date,
    announced_on      date,
    language          text        not null check (language in ('en', 'hi', 'gu')),
    source_url        text        not null,
    source_path       text        not null,
    source_sha256     text        not null,
    source_release_id text        not null,
    ministry          text        not null,
    title             text        not null,
    posted_on         date        not null,
    chunk_index       integer     not null,
    raw_start         integer     not null,
    raw_end           integer     not null,
    text              text        not null,
    embedding         extensions.vector(768) not null,
    embedding_model   text        not null
);

create index if not exists chunks_scheme_version_idx on public.chunks (scheme, version);
create index if not exists chunks_embedding_idx
    on public.chunks using hnsw (embedding extensions.vector_cosine_ops);

-- Row level security on; the demo backend connects with the database password
-- (which bypasses RLS), and the public API keys get read-only access.
alter table public.chunks enable row level security;

drop policy if exists "chunks are readable by everyone" on public.chunks;
create policy "chunks are readable by everyone"
    on public.chunks for select to anon, authenticated using (true);

-- Filtered nearest-neighbour search mirroring policydrift.retrieval.search.Filters.
create or replace function public.match_chunks(
    query_embedding extensions.vector(768),
    match_count     integer default 5,
    filter_scheme   text    default null,
    filter_language text    default null,
    filter_versions text[]  default null,
    as_of           date    default null,
    current_only    boolean default false
)
returns table (chunk_id text, scheme text, version text, language text, text text, score float)
language sql stable
set search_path = public, extensions
as $$
    select c.chunk_id, c.scheme, c.version, c.language, c.text,
           1 - (c.embedding <=> query_embedding) as score
    from public.chunks c
    where (filter_scheme   is null or c.scheme   = filter_scheme)
      and (filter_language is null or c.language = filter_language)
      and (filter_versions is null or c.version  = any (filter_versions))
      and (not current_only or c.effective_to is null)
      and (as_of is null or c.effective_from is null or c.effective_from <= as_of)
      and (as_of is null or c.effective_to   is null or as_of <= c.effective_to)
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
