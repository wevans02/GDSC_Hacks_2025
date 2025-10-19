import 'dart:ui';
import 'package:flutter/material.dart';
import '../../core/constants.dart';

class MessageBubble extends StatelessWidget {
  const MessageBubble({
    super.key,
    required this.isUser,
    required this.isLoading,
    required this.child,
    this.introCity,
  });

  final bool isUser;
  final bool isLoading;
  final Widget child;
  final String? introCity;

  @override
  Widget build(BuildContext context) {
    final bubbleColor = isUser ? kUserBubbleColor : kAiBubbleColor;
    final borderRadius = BorderRadius.only(
      topLeft: const Radius.circular(18),
      topRight: const Radius.circular(18),
      bottomLeft: Radius.circular(isUser ? 18 : 4),
      bottomRight: Radius.circular(isUser ? 4 : 18),
    );

    return ClipRRect(
      borderRadius: borderRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 8.0, sigmaY: 8.0),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(color: bubbleColor, borderRadius: borderRadius),
          child: child,
        ),
      ),
    );
  }
}
