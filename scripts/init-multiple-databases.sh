#!/bin/bash
set -e

# Se connecter en tant que super-utilisateur pour créer les autres rôles et bases
export PGPASSWORD=$POSTGRES_PASSWORD

# Fonction pour créer un utilisateur et une base de données
# Prend en paramètres : USER, PASSWORD, DATABASE
create_db_and_user() {
  local user=$1
  local password=$2
  local db=$3

  # Vérifie si le mot de passe est 'none' ou vide, et ajuste la commande SQL
  # NOTE: Un mot de passe vide est une mauvaise pratique, mais géré ici pour la flexibilité en dev
  if [[ -z "$password" || "$password" == "none" ]]; then
    password_clause="WITH PASSWORD NULL" # Crée un rôle sans mot de passe, désactivant le login par mot de passe
    echo "Creating user '$user' with a NULL password (login will likely fail without other auth methods)."
  else
    password_clause="WITH PASSWORD '$password'"
    echo "Creating user '$user' with a specified password."
  fi

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
      -- Créer l'utilisateur s'il n'existe pas déjà
      DO \$\$
      BEGIN
          IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$user') THEN
              CREATE USER $user $password_clause;
          END IF;
      END
      \$\$;

      -- Créer la base de données si elle n'existe pas
      SELECT 'CREATE DATABASE $db'
      WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec

      -- Donner tous les privilèges sur la base à l'utilisateur
      GRANT ALL PRIVILEGES ON DATABASE $db TO $user;
EOSQL
}

# --- Création des bases et utilisateurs ---

# 1. Pour N8N
if [[ -n "$N8N_DB_USER" && -n "$N8N_DB_NAME" ]]; then
  echo "--- Provisioning N8N Database ---"
  create_db_and_user "$N8N_DB_USER" "$N8N_DB_PASSWORD" "$N8N_DB_NAME"
  echo "N8N database and user provisioned."
fi

# 2. Pour l'application MY-IA
if [[ -n "$APP_DB_USER" && -n "$APP_DB_NAME" ]]; then
  echo "--- Provisioning Application Database ---"
  create_db_and_user "$APP_DB_USER" "$APP_DB_PASSWORD" "$APP_DB_NAME"
  echo "Application database and user provisioned."
fi

echo "--- Database initialization script finished ---"
