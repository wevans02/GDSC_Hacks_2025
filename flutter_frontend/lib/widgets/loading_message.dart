import 'dart:async';
import 'package:flutter/material.dart';
import '../main.dart';

const loadingSteps = [
  "Searching bylaws...",
  "Analyzing relevant sections...",
  "Generating natural language response...",
];

class LoadingMessage extends StatefulWidget {
  const LoadingMessage({super.key});

  @override
  State<LoadingMessage> createState() => _LoadingMessageState();
}

class _LoadingMessageState extends State<LoadingMessage> {
  int index = 0;
  late final Timer timer;

  @override
  void initState() {
    super.initState();
    timer = Timer.periodic(const Duration(seconds: 2), (t) {
      setState(() {
        index = (index + 1) % loadingSteps.length;
      });
    });
  }

  @override
  void dispose() {
    timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Text(
      loadingSteps[index],
      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: kAccentColor,
            fontStyle: FontStyle.italic,
          ),
    );
  }
}
