class ChatMessage {
  final String text;
  final DateTime time;
  final bool fromMe;
  final List<Map<String, dynamic>>? sources;
  final bool isLoading;
  final Map<String, dynamic>? context;

  const ChatMessage({
    required this.text,
    required this.time,
    required this.fromMe,
    this.sources,
    this.isLoading = false,
    this.context,
  });

  ChatMessage copyWith({
    String? text,
    DateTime? time,
    bool? fromMe,
    List<Map<String, dynamic>>? sources,
    bool? isLoading,
    Map<String, dynamic>? context,
  }) {
    return ChatMessage(
      text: text ?? this.text,
      time: time ?? this.time,
      fromMe: fromMe ?? this.fromMe,
      sources: sources ?? this.sources,
      isLoading: isLoading ?? this.isLoading,
      context: context ?? this.context,
    );
  }
}
