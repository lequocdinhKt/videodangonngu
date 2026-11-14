-- The public experience has exactly two editorial chapters.  Keep the
-- production-video UUID mapping in the database so an admin can replace a
-- chapter without a frontend deploy.
CREATE TABLE public_video_slots (
    slot_key VARCHAR(32) PRIMARY KEY,
    video_id UUID UNIQUE REFERENCES videos (id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT public_video_slots_key_check
        CHECK (slot_key IN ('chapter-1', 'chapter-2'))
);

INSERT INTO public_video_slots (slot_key)
VALUES ('chapter-1'), ('chapter-2')
ON CONFLICT (slot_key) DO NOTHING;
