def migrate(cr, version):
    """Let the director's secretary sign in with the same UAT password as the director."""
    cr.execute(
        """
        UPDATE res_users AS sec
           SET password = dir.password,
               company_id = COALESCE(sec.company_id, dir.company_id)
          FROM res_users AS dir
         WHERE sec.login = 'uat.secretary'
           AND dir.login = 'uat.director'
           AND (sec.password IS NULL OR sec.password = '')
        """
    )
    cr.execute(
        """
        UPDATE res_partner AS sec_partner
           SET lang = dir_partner.lang
          FROM res_users AS sec
          JOIN res_users AS dir ON dir.login = 'uat.director'
          JOIN res_partner AS dir_partner ON dir_partner.id = dir.partner_id
         WHERE sec.login = 'uat.secretary'
           AND sec_partner.id = sec.partner_id
           AND (sec_partner.lang IS NULL OR sec_partner.lang = '')
        """
    )
