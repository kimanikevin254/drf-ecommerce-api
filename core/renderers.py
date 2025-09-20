from rest_framework.renderers import JSONRenderer

class StandardJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')

        if response and response.status_code >= 400:
            # Already formatted by exception handler
            return super().render(data, accepted_media_type, renderer_context)
        else:
            # Success response
            custom_response = {
                'success': True,
                'errors': False,
                'data': data
            }

            return super().render(custom_response, accepted_media_type, renderer_context)