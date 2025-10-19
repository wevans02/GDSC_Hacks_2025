import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/constants.dart';

class LoadingMessage extends StatefulWidget {
  const LoadingMessage({super.key});

  @override
  State<LoadingMessage> createState() => _LoadingMessageState();
}

class _LoadingMessageState extends State<LoadingMessage> {
  int index = 0;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    timer = Timer.periodic(const Duration(seconds: 2), (_) {
      if (!mounted) return;
      setState(() => index = (index + 1) % loadingSteps.length);
    });
  }

  @override
  void dispose() {
    timer?.cancel();
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
