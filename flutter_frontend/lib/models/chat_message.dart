
class ChatMessage {
  final String text;
  final DateTime time;
  final bool fromMe;
  final List<Map<String, dynamic>>? sources;
  final bool isLoading;
  final Map<String, dynamic>? context; // Additional context for conversation

  ChatMessage({
    required this.text,
    required this.time,
    required this.fromMe,
    this.sources,
    this.isLoading = false,
    this.context,
  });
}
