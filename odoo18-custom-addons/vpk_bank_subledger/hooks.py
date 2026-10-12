# -*- coding: utf-8 -*-


def post_init_hook(env):
    env["vpk.bank.subledger.account"].load_opening_snapshot()
