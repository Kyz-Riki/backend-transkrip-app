CREATE TABLE IF NOT EXISTS public.summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id VARCHAR(20) NOT NULL UNIQUE,
    url TEXT NOT NULL,
    transcript TEXT NOT NULL,
    summary TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Migration for existing table:
-- ALTER TABLE public.summaries ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_summaries_video_id ON public.summaries(video_id);
CREATE INDEX IF NOT EXISTS idx_summaries_user_id ON public.summaries(user_id);

ALTER TABLE public.summaries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access" ON public.summaries
    FOR SELECT USING (true);

CREATE POLICY "Allow anon insert access" ON public.summaries
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anon update access" ON public.summaries
    FOR UPDATE USING (true);

