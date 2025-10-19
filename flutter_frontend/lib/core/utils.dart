import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

Future<void> launchExternalUrl(BuildContext context, String urlString) async {
  final Uri url = Uri.parse(urlString);
  final ok = await launchUrl(url, mode: LaunchMode.externalApplication);
  if (!ok && context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Could not open link: $urlString'), backgroundColor: Colors.redAccent),
    );
  }
}

Future<void> animateScrollToBottom(ScrollController scroll, {Duration duration = const Duration(milliseconds: 300)}) async {
  if (!scroll.hasClients) return;
  await scroll.animateTo(
    scroll.position.maxScrollExtent,
    duration: duration,
    curve: Curves.easeOut,
  );
}
