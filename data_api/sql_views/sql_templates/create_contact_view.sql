CREATE OR REPLACE VIEW contacts_with_orgs AS
    SELECT
        contacts.*,
        orgs.name as org_name,
        orgs.country as org_country
    FROM staging_contact contacts
    LEFT JOIN staging_organization orgs
            ON contacts.organization_id = orgs.id;
