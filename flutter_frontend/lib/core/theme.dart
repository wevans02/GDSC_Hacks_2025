import 'package:flutter/material.dart';
import 'constants.dart';

ColorScheme buildColorScheme(ThemeData baseDark) {
  return ColorScheme.fromSeed(
    seedColor: kAccentColor,
    brightness: Brightness.dark,
    primary: kAccentColor,
    secondary: kUserBubbleColor,
    background: kBgDark,
    surface: kAiBubbleColor,
  );
}

InputDecorationTheme buildInputDecorationTheme() {
  return InputDecorationTheme(
    filled: true,
    fillColor: const Color(0x33FFFFFF),
    hintStyle: TextStyle(color: Colors.white.withOpacity(0.6)),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(30.0),
      borderSide: BorderSide.none,
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(30.0),
      borderSide: const BorderSide(color: kAccentColor, width: 1.5),
    ),
    contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
  );
}

IconButtonThemeData buildIconButtonTheme() {
  return IconButtonThemeData(
    style: IconButton.styleFrom(
      foregroundColor: kAccentColor,
      backgroundColor: Colors.white.withOpacity(0.2),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
    ),
  );
}

ChipThemeData buildChipTheme() {
  return const ChipThemeData(
    backgroundColor: kSourceChipColor,
    labelStyle: TextStyle(
      color: kSourceChipTextColor,
      fontSize: 11,
      fontWeight: FontWeight.w500,
    ),
    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
    shape: StadiumBorder(),
  );
}
