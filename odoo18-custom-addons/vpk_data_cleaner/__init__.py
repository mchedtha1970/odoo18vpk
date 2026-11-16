# -*- coding: utf-8 -*-
from . import models
from . import wizard


def post_init_hook(env):
    """สร้างรายการ Module และ Model พร้อมจำแนก Master / Transaction ทันทีหลังติดตั้ง"""
    env["vpk.data.cleaner.module"].sudo().action_sync_all()
