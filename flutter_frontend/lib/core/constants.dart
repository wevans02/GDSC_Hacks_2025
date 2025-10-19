import 'package:flutter/material.dart';

// Colors
final Color kBgDark = Colors.grey[900]!;
const Color kBgLight = Color(0xFF3F51B5); // Indigo
const Color kAccentColor = Color(0xFF00BCD4); // Cyan
const Color kUserBubbleColor = Color(0x77FFFFFF);
const Color kAiBubbleColor = Colors.transparent;
const Color kTextColor = Colors.white;
const Color kSourceChipColor = Color(0xFFB2EBF2);
const Color kSourceChipTextColor = Colors.black87;

// Timings
const Duration kAnimationDuration = Duration(milliseconds: 400);
const Duration kTransitionDuration = Duration(milliseconds: 500);

// Loading steps
const loadingSteps = [
  "Searching bylaws...",
  "Analyzing relevant sections...",
  "Generating natural language response...",
];

// Cities
const List<String> kAvailableCities = ['Toronto', 'Waterloo', 'Guelph'];

// API
const String kApiBase = 'http://127.0.0.1:5000';
