from collections import defaultdict

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    post_model = env["account.budget.post"].sudo()
    budget_line_model = env["budget.lines"].sudo()
    request_line_model = env["departmental.budget.request.line"].sudo()

    material_posts = post_model.search([("material_sub_type_id", "!=", False)])
    if not material_posts:
        return

    def get_root(post):
        root = post
        while root.parent_budget_post_id:
            root = root.parent_budget_post_id
        return root

    groups = defaultdict(list)
    for post in material_posts:
        root = get_root(post)
        key = (post.company_id.id, root.id, post.material_sub_type_id.id)
        groups[key].append(post)

    for posts in groups.values():
        root_post = get_root(posts[0])
        sub_type = posts[0].material_sub_type_id
        expected_name = post_model._build_material_budget_post_name(root_post, sub_type)
        canonical = min(posts, key=lambda post: post.id)

        for post in posts:
            if post.id == canonical.id:
                continue
            budget_line_model.search([("general_budget_id", "=", post.id)]).write(
                {"general_budget_id": canonical.id}
            )
            request_line_model.search([("budget_post_id", "=", post.id)]).write(
                {"budget_post_id": root_post.id}
            )
            post.unlink()

        canonical.write(
            {
                "name": expected_name,
                "parent_budget_post_id": root_post.id,
                "budget_group_id": sub_type.budget_group_id.id,
                "account_ids": [(6, 0, root_post.account_ids.ids)],
            }
        )

    request_lines = request_line_model.search(
        [
            ("budget_post_id.parent_budget_post_id", "!=", False),
            ("material_sub_type_id", "!=", False),
        ]
    )
    for line in request_lines:
        root_post = get_root(line.budget_post_id)
        if line.budget_post_id != root_post:
            line.write({"budget_post_id": root_post.id})
