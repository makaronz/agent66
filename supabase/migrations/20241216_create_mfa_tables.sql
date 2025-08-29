-- Create MFA tracking table
CREATE TABLE IF NOT EXISTS public.user_mfa_methods (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    totp_enabled BOOLEAN DEFAULT FALSE,
    totp_secret TEXT,
    webauthn_enabled BOOLEAN DEFAULT FALSE,
    webauthn_credentials JSONB DEFAULT '[]'::jsonb,
    webauthn_challenge TEXT,
    backup_codes_enabled BOOLEAN DEFAULT FALSE,
    backup_codes_hash TEXT[],
    sms_enabled BOOLEAN DEFAULT FALSE,
    sms_phone_number TEXT,
    last_mfa_update TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create MFA backup codes table for better security
CREATE TABLE IF NOT EXISTS public.user_backup_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    code_hash TEXT NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '1 year')
);

-- Create MFA audit log table
CREATE TABLE IF NOT EXISTS public.mfa_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action TEXT NOT NULL, -- 'setup', 'verify', 'disable', 'backup_used'
    method TEXT NOT NULL, -- 'totp', 'webauthn', 'sms', 'backup_code'
    success BOOLEAN NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on all MFA tables
ALTER TABLE public.user_mfa_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_backup_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mfa_audit_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_mfa_methods
CREATE POLICY "Users can manage their own MFA methods"
ON public.user_mfa_methods
FOR ALL
TO authenticated
USING (auth.uid() = user_id);

-- RLS Policies for user_backup_codes
CREATE POLICY "Users can manage their own backup codes"
ON public.user_backup_codes
FOR ALL
TO authenticated
USING (auth.uid() = user_id);

-- RLS Policies for mfa_audit_log
CREATE POLICY "Users can view their own MFA audit log"
ON public.mfa_audit_log
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Service can insert MFA audit logs"
ON public.mfa_audit_log
FOR INSERT
TO service_role
WITH CHECK (true);

-- Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_mfa_methods TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_backup_codes TO authenticated;
GRANT SELECT ON public.mfa_audit_log TO authenticated;

-- Grant permissions to anon users (for public access if needed)
GRANT SELECT ON public.user_mfa_methods TO anon;
GRANT SELECT ON public.user_backup_codes TO anon;
GRANT SELECT ON public.mfa_audit_log TO anon;

-- Create indexes for better performance
CREATE INDEX idx_user_mfa_methods_user_id ON public.user_mfa_methods(user_id);
CREATE INDEX idx_user_backup_codes_user_id ON public.user_backup_codes(user_id);
CREATE INDEX idx_user_backup_codes_used ON public.user_backup_codes(used) WHERE used = false;
CREATE INDEX idx_mfa_audit_log_user_id ON public.mfa_audit_log(user_id);
CREATE INDEX idx_mfa_audit_log_created_at ON public.mfa_audit_log(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_user_mfa_methods_updated_at
    BEFORE UPDATE ON public.user_mfa_methods
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to initialize MFA methods for new users
CREATE OR REPLACE FUNCTION initialize_user_mfa()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_mfa_methods (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to initialize MFA methods for new users
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION initialize_user_mfa();