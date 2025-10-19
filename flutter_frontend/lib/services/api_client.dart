import 'dart:convert';
import 'package:http/http.dart' as http;

import '../core/constants.dart';

class ApiClient {
  ApiClient({http.Client? httpClient}) : _http = httpClient ?? http.Client();

  final http.Client _http;

  Uri _uri(String path) => Uri.parse('$kApiBase$path');

  Future<Map<String, dynamic>> requestQuery({
    required String query,
    required String city,
    required List<Map<String, dynamic>> conversationContext,
  }) async {
    final res = await _http.post(
      _uri('/api/query'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'query': query,
        'city': city,
        'conversation_context': conversationContext.take(3).toList(),
        'timestamp': DateTime.now().toIso8601String(),
      }),
    );

    if (res.statusCode != 200) {
      return {
        'ai_response': '⚠️ Server Error ${res.statusCode}. Please try again later.',
        'retrieved_sources': <Map<String, dynamic>>[],
      };
    }

    final decoded = jsonDecode(res.body) as Map<String, dynamic>;
    final sourcesDyn = decoded['retrieved_sources'] as List<dynamic>?;
    final sources = sourcesDyn?.whereType<Map<String, dynamic>>().toList() ?? <Map<String, dynamic>>[];

    return {
      'ai_response': decoded['ai_response'] as String? ?? 'Error: No AI response received.',
      'retrieved_sources': sources,
    };
  }

  Future<bool> requestCity({required String city, String? email}) async {
    final res = await _http.post(
      _uri('/api/request-city'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'city': city, if (email != null && email.isNotEmpty) 'email': email}),
    );
    return res.statusCode >= 200 && res.statusCode < 300;
  }

  void dispose() => _http.close();
}
