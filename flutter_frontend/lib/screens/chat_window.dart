import 'dart:async';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter/gestures.dart';


import '../core/constants.dart';
import '../core/types.dart';
import '../core/utils.dart';
import '../services/api_client.dart';
import '../widgets/chat/loading_message.dart';
import '../widgets/chat/message_bubble.dart';
import '../widgets/chat/source_strip.dart';


class _DragScrollBehavior extends MaterialScrollBehavior {
  @override
  Set<PointerDeviceKind> get dragDevices => {
        PointerDeviceKind.touch,
        PointerDeviceKind.mouse,
        PointerDeviceKind.stylus,
        PointerDeviceKind.invertedStylus,
        PointerDeviceKind.unknown,
      };
}

class ChatWindow extends StatefulWidget {
  const ChatWindow({super.key, this.initialQuery, this.selectedCity = 'Toronto'});

  final String? initialQuery;
  final String selectedCity;

  @override
  State<ChatWindow> createState() => _ChatWindowState();
}

class _ChatWindowState extends State<ChatWindow> {
  final _messages = <ChatMessage>[];
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final _focus = FocusNode();
  final _api = ApiClient();

  bool _canSend = true;
  static const _cooldown = Duration(seconds: 3);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if ((widget.initialQuery ?? '').trim().isNotEmpty) {
        _processQuery(widget.initialQuery!.trim());
      } else {
        if (mounted) {
          _messages.add(ChatMessage(
            text: "",
            time: DateTime.now(),
            fromMe: false,
            context: {'introCity': widget.selectedCity},
          ));
          setState(() {});
        }
      }
    });
  }

  @override
  void dispose() {
    _focus.dispose();
    _input.dispose();
    _scroll.dispose();
    _api.dispose();
    super.dispose();
  }

  Future<void> _processQuery(String query) async {
    if (query.isEmpty) return;

    final conversationContext = _messages
        .where((m) => !m.isLoading)
        .map((m) => {
              'fromMe': m.fromMe,
              'text': m.text,
              'timestamp': m.time.toIso8601String(),
            })
        .toList();

    // Add user + loading message
    setState(() {
      _messages.add(ChatMessage(
        text: query,
        time: DateTime.now(),
        fromMe: true,
        context: {'city': widget.selectedCity},
      ));
      _canSend = false;
      _messages.add(ChatMessage(
        text: '...',
        time: DateTime.now(),
        fromMe: false,
        isLoading: true,
      ));
    });
    await Future.microtask(() => animateScrollToBottom(_scroll));

    Map<String, dynamic> result;

    try {
      result = await _api.requestQuery(
        query: query,
        city: widget.selectedCity,
        conversationContext: conversationContext,
      );
    } catch (e) {
      // Handle network/CORS/other request errors
      result = {
        'ai_response':
            '⚠️ Network or CORS Error.\n\nMake sure the backend server is running and accessible (check browser console for details).',
        'retrieved_sources': <Map<String, dynamic>>[],
      };

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('⚠️ Network or CORS error — see chat for details.'),
            backgroundColor: Colors.redAccent,
            duration: Duration(seconds: 4),
          ),
        );
      }
    }

    final aiText = result['ai_response'] as String? ??
        '⚠️ Unknown error occurred. Please try again.';
    final rawSources =
        (result['retrieved_sources'] as List<Map<String, dynamic>>?) ?? [];

    // Deduplicate and limit sources
    final seenTitles = <String>{};
    final sources = rawSources.where((s) {
      final t = s['title'];
      if (t == null || (t is String && t.trim().isEmpty)) return false;
      if (seenTitles.contains(t)) return false;
      seenTitles.add(t);
      return true;
    }).take(12).toList();

    // Always replace loading message, even on errors
    setState(() {
      final idx = _messages.lastIndexWhere((m) => m.isLoading);
      if (idx != -1) {
        _messages[idx] = ChatMessage(
          text: aiText,
          time: DateTime.now(),
          fromMe: false,
          sources: sources,
          isLoading: false,
        );
      } else {
        _messages.add(ChatMessage(
          text: aiText,
          time: DateTime.now(),
          fromMe: false,
          sources: sources,
          isLoading: false,
        ));
      }
    });

    // Restore send ability after cooldown
    Timer(_cooldown, () {
      if (mounted) setState(() => _canSend = true);
    });

    await Future.delayed(const Duration(milliseconds: 100));
    await animateScrollToBottom(_scroll);
  }


  void _send() {
    final text = _input.text;
    final trimmed = text.trim();
    if (!_canSend || trimmed.isEmpty) return;
    _input.clear();
    _processQuery(trimmed);
  }


  Widget _introMessage(String city) {
    return RichText(
      text: TextSpan(
        style: const TextStyle(
          fontSize: 18,
          color: Colors.white,
          height: 1.4,
        ),
        children: [
          const TextSpan(text: "Hello! I'm your AI assistant for "),
          WidgetSpan(
            alignment: PlaceholderAlignment.baseline,
            baseline: TextBaseline.alphabetic,
            child: ShaderMask(
              shaderCallback: (bounds) => const LinearGradient(
                colors: [Colors.cyan, Colors.tealAccent],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ).createShader(bounds),
              blendMode: BlendMode.srcIn,
              child: Text(
                city,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.white, // this will be replaced by gradient
                ),
              ),
            ),
          ),
          const TextSpan(
            text:
                " municipal bylaws. I can help you understand noise regulations, "
                "parking rules, zoning restrictions, and much more. What would you like to know?",
          ),
        ],
      ),
    );
  }

  final List<String> _examplePrompts = const [
    "What are the rules for parking overnight?",
    "What are the noise bylaw hours?",
    "Can I build a fence in my backyard?",
    "What are snow removal rules?",
  ];



  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            controller: _scroll,
            padding: const EdgeInsets.symmetric(vertical: 15.0, horizontal: 10.0),
            itemCount: _messages.length,
            itemBuilder: (context, i) {
              final m = _messages[i];
              return _buildMessageItem(context, m)
                  .animate()
                  .fadeIn(duration: kAnimationDuration)
                  .slideY(begin: 0.2, duration: kAnimationDuration, curve: Curves.easeOutCubic);
            },
          ),
        ),

        // --- Example prompts appear only when field empty & no user msgs ---
        if (_messages.length <= 1 && _input.text.isEmpty)
          _buildExamplePrompts(),

        _buildInputArea(context),
      ],
    );

  }

  Widget _buildMessageItem(BuildContext context, ChatMessage message) {
    final bool isUser = message.fromMe;
    final alignment = isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start;
    final marginEdge = isUser ? const EdgeInsets.only(left: 40.0) : const EdgeInsets.only(right: 0.0);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0).add(marginEdge),
      child: Column(
        crossAxisAlignment: alignment,
        children: [
          Row(
            mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Flexible(
                child: MessageBubble(
                  isUser: isUser,
                  isLoading: message.isLoading,
                  introCity: message.context?['introCity'],
                  child: message.isLoading
                      ? const LoadingMessage()
                      : (message.context?['introCity'] != null)
                          ? _introMessage(message.context!['introCity'])
                          : MarkdownBody(
                              data: message.text,
                              selectable: true,
                              styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
                                p: Theme.of(context).textTheme.bodyLarge?.copyWith(color: kTextColor, height: 1.4),
                                a: const TextStyle(
                                  color: kAccentColor,
                                  decoration: TextDecoration.underline,
                                  decorationColor: kAccentColor,
                                ),
                              ),
                              onTapLink: (text, href, title) {
                                if (href != null) launchExternalUrl(context, href);
                              },
                            ),
                ),
              ),
              if (isUser) ...[
                const SizedBox(width: 8),
                Icon(Icons.person_outline, color: Colors.white.withOpacity(0.8), size: 24),
              ],
            ],
          ),
          if (!isUser && (message.sources?.isNotEmpty ?? false) && !message.isLoading)
            SourcesStrip(
              sources: message.sources!,
              onOpenUrl: (url) => launchExternalUrl(context, url),
            ),
        ],
      ),
    );
  }

  Widget _buildInputArea(BuildContext context) {
    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10.0, sigmaY: 10.0),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 15.0, vertical: 10.0).copyWith(bottom: 10),
          child: Row(
            children: [
              Expanded( 
                child: TextField( 
                  onChanged: (String value) {
                    // Check if sending is allowed and the input isn't empty after trimming 
                    if (_canSend && value.trim().isNotEmpty && value.endsWith("\n")) { _send(); } 
                  },
                  
                  controller: _input, 
                  maxLines: null, 
                  keyboardType: TextInputType.multiline, 
                  style: TextStyle(color: kTextColor), 
                  decoration: const InputDecoration( 
                    hintText: 'Ask a question...', ), 
                    inputFormatters: [ LengthLimitingTextInputFormatter(500), ], 
                  ), 
                ),
              const SizedBox(width: 10),
              IconButton(
                icon: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  transitionBuilder: (child, animation) => ScaleTransition(scale: animation, child: child),
                  child: Icon(
                    _canSend ? Icons.send_rounded : Icons.hourglass_empty_rounded,
                    key: ValueKey<bool>(_canSend),
                    color: _canSend ? kAccentColor : Colors.grey.shade500,
                    size: 24,
                  ),
                ),
                tooltip: _canSend ? 'Send message' : 'Please wait...',
                onPressed: _canSend ? _send : null,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildExamplePrompts() {
    final prompts = _examplePrompts;

    return SizedBox(
      height: 48, // a bit taller to allow chip shadow and spacing
      child: Stack(
        children: [
          ScrollConfiguration(
            behavior: _DragScrollBehavior(), // reuse same as source cards
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              itemCount: prompts.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, i) {
                final prompt = prompts[i];
                return ActionChip(
                  backgroundColor: Colors.white.withOpacity(0.1),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20),
                  ),
                  label: Text(
                    prompt,
                    style: const TextStyle(color: Colors.white, fontSize: 16),
                  ),
                  onPressed: () => _processQuery(prompt),
                );
              },
            ),
          ),

          // Optional subtle fade on left/right edges
          Positioned(
            left: 0,
            top: 0,
            bottom: 0,
            width: 20,
            child: IgnorePointer(
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.centerLeft,
                    end: Alignment.centerRight,
                    colors: [kBgDark, kBgDark.withOpacity(0)],
                  ),
                ),
              ),
            ),
          ),
          Positioned(
            right: 0,
            top: 0,
            bottom: 0,
            width: 20,
            child: IgnorePointer(
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.centerRight,
                    end: Alignment.centerLeft,
                    colors: [kBgDark, kBgDark.withOpacity(0)],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }


}


