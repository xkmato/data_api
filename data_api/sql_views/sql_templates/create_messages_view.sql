CREATE OR REPLACE VIEW messages_with_orgs AS
    SELECT
        messages.*,
        orgs.name as org_name,
        orgs.country as org_country
    FROM staging_message messages
    LEFT JOIN staging_organization orgs
            ON messages.organization_id = orgs.id;
