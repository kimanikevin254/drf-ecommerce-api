from rest_framework.renderers import JSONRenderer

class StandardJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')

        if response and response.status_code >= 400:
            # Check if error response already in standardized format
            if (
                isinstance(data, dict)
                and 'success' in data
                and 'errors' in data
                and 'data' in data
            ):
                print('already formatted mahn')
                # Already formatted by exception handler
                return super().render(data, accepted_media_type, renderer_context)
            else:
                # Raw error (like a string passed in Response)
                if isinstance(data, dict):
                    errors = data
                else:
                    errors = [str(data)]

                standardized = {
                    'success': False,
                    'errors': errors,
                    'data': None
                }
                return super().render(standardized, accepted_media_type, renderer_context)

        # Success response
        custom_response = {
            'success': True,
            'errors': None,
            'data': data
        }
        return super().render(custom_response, accepted_media_type, renderer_context)
