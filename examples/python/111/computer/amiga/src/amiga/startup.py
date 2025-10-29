import workbench.workbench as wb


def get_tasks():
    return ["Run startup-sequence"] + ["Show %s" % icon for icon in wb.get_icons()]
