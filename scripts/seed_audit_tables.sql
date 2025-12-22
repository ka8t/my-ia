-- Seed data for audit_actions (from CAHIER_DES_CHARGES_AUTH.md)
INSERT INTO audit_actions (name, display_name, severity) VALUES
    ('login_success', 'Connexion réussie', 'info'),
    ('login_failed', 'Échec de connexion', 'warning'),
    ('logout', 'Déconnexion', 'info'),
    ('user_created', 'Utilisateur créé', 'info'),
    ('user_updated', 'Utilisateur modifié', 'info'),
    ('user_deleted', 'Utilisateur supprimé', 'warning'),
    ('role_changed', 'Rôle modifié', 'warning'),
    ('user_activated', 'Compte activé', 'info'),
    ('user_deactivated', 'Compte désactivé', 'warning'),
    ('password_reset_requested', 'Réinitialisation mot de passe demandée', 'info'),
    ('password_reset_completed', 'Mot de passe réinitialisé', 'warning'),
    ('password_changed', 'Mot de passe modifié', 'info'),
    ('document_uploaded', 'Document uploadé', 'info'),
    ('document_deleted', 'Document supprimé', 'warning'),
    ('conversation_created', 'Conversation créée', 'info'),
    ('conversation_deleted', 'Conversation supprimée', 'info'),
    ('preferences_updated', 'Préférences modifiées', 'info'),
    ('preferences_updated_by_admin', 'Préférences modifiées par admin', 'warning'),
    ('config_updated', 'Configuration modifiée', 'warning'),
    ('admin_action', 'Action administrative', 'warning')
ON CONFLICT (name) DO NOTHING;

-- Seed data for resource_types (from CAHIER_DES_CHARGES_AUTH.md lines 515-521)
INSERT INTO resource_types (name, display_name) VALUES
    ('user', 'Utilisateur'),
    ('conversation', 'Conversation'),
    ('document', 'Document'),
    ('preference', 'Préférence'),
    ('config', 'Configuration')
ON CONFLICT (name) DO NOTHING;

-- Seed data for conversation_modes (from CAHIER_DES_CHARGES_AUTH.md lines 500-503)
INSERT INTO conversation_modes (name, display_name, description) VALUES
    ('chatbot', 'ChatBot', 'Mode conversationnel général avec RAG'),
    ('assistant', 'Assistant', 'Mode orienté tâches et procédures')
ON CONFLICT (name) DO NOTHING;
