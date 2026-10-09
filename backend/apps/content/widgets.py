from typing import Any

from django import forms


class MarkdownPreviewWidget(forms.Textarea):
    """Textarea with a live preview rendered by the shared frontend renderer (architecture 9).

    `links` maps slugs to {"title", "href"} so [[slug]] links resolve in the preview.
    `images` maps positions to {"src", "caption", "credit"} for ![[position]] images.
    """

    template_name = "content/widgets/markdown_preview.html"

    class Media:
        css = {"all": ["content/admin/markdown-preview.css"]}
        js = ["content/admin/markdown-preview.js"]

    def __init__(
        self,
        links: dict[str, dict[str, str | None]] | None = None,
        images: dict[str, dict[str, str]] | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.links = links or {}
        self.images = images or {}

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        widget_id = context["widget"]["attrs"].get("id", name)
        context["widget"]["refs"] = {"links": self.links, "images": self.images}
        context["widget"]["refs_id"] = f"{widget_id}-refs"
        return context
