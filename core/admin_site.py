from django.contrib.admin import AdminSite


class KnowledgeAdminSite(AdminSite):
    site_header = "Knowledge Base"
    site_title = "Knowledge Base Admin"
    index_title = "Knowledge Management"

    def get_app_list(self, request, app_label=None):
        # Django's get_app_list accepts an optional app_label argument
        app_list = super().get_app_list(request, app_label)

        # Map model object names to their target custom group
        groups = {
            "Articles": ["Article", "ArticleCategory", "ArticleSubcategory", "ArticleTag"],
            "Journals": ["Journal", "JournalCategory", "JournalSubcategory", "JournalTag"],
            "Notes": ["Note", "NoteCategory", "NoteSubcategory", "NoteTag"],
            "Strategies": ["Strategy", "StrategyCategory", "StrategySubcategory", "StrategyTag"],
            "Goals": ["Goal", "GoalCategory", "GoalSubcategory", "GoalTag"],
            "Decisions": ["Decision", "DecisionCategory", "DecisionSubcategory", "DecisionTag"],
            "Central Points": ["CentralPoint", "CentralPointCategory", "CentralPointSubcategory", "CentralPointTag"],
        }

        # Initialize a dictionary to temporarily collect matched models for each group
        grouped_models = {group_name: [] for group_name in groups}

        # Flatten and extract models from Django's default app list
        for app in app_list:
            for model in app["models"]:
                model_name = model["object_name"]
                
                # Check which group this model belongs to
                for group_name, allowed_models in groups.items():
                    if model_name in allowed_models:
                        grouped_models[group_name].append(model)
                        break  # Found its home, stop checking other groups

        custom_apps = []

        # Reconstruct the app structure based on your custom groups
        for group_name, models in grouped_models.items():
            if not models:
                continue

            # Optional: Sort models within the group to match the order defined in your dict
            order_list = groups[group_name]
            models.sort(key=lambda x: order_list.index(x["object_name"]) if x["object_name"] in order_list else 99)

            custom_apps.append({
                "name": group_name,
                "app_label": group_name.lower().replace(" ", "_"),
                "app_url": "",
                "has_module_perms": True,
                "models": models,
            })

        # If Django asked for a specific app layout, filter for it, otherwise return full custom list
        return custom_apps


admin_site = KnowledgeAdminSite(name="knowledge_admin")