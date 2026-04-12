from django.urls import reverse_lazy

UNFOLD = {
    "SITE_TITLE": "Teaching Platform Admin",
    "SITE_HEADER": "Interactive Teaching Platform",
    "SITE_SYMBOL": "school",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Dashboard",
                "separator": False,
                "collapsible": False,
                "items": [
                    {
                        "title": "Overview",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin_dashboard"),
                    },
                ],
            },
            {
                "title": "Content Management",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": reverse_lazy("admin:content_category_changelist"),
                    },
                    {
                        "title": "Sub Categories",
                        "icon": "account_tree",
                        "link": reverse_lazy("admin:content_subcategory_changelist"),
                    },
                    {
                        "title": "Subjects",
                        "icon": "menu_book",
                        "link": reverse_lazy("admin:content_subject_changelist"),
                    },
                    {
                        "title": "Accordion Sections",
                        "icon": "view_agenda",
                        "link": reverse_lazy("admin:content_accordionsection_changelist"),
                    },
                    {
                        "title": "Interactive Contents",
                        "icon": "interactive_space",
                        "link": reverse_lazy("admin:content_interactivecontent_changelist"),
                    },
                ],
            },
            {
                "title": "Authentication",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": "Groups",
                        "icon": "groups",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
}
