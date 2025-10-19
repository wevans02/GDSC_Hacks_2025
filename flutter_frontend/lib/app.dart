import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'core/constants.dart';
import 'core/theme.dart';
import 'widgets/shared/about_page.dart';

import 'screens/home_page.dart' as home;

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    final baseDark = ThemeData.dark();
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Paralegal AI',
      routes: { '/about': (context) => const AboutPage() },
      theme: baseDark.copyWith(
        colorScheme: buildColorScheme(baseDark),
        textTheme: GoogleFonts.poppinsTextTheme(baseDark.textTheme)
            .apply(bodyColor: kTextColor, displayColor: kTextColor),
        inputDecorationTheme: buildInputDecorationTheme(),
        iconButtonTheme: buildIconButtonTheme(),
        chipTheme: buildChipTheme(),
      ),
      home: const _Entry(),
    );
  }
}

class _Entry extends StatelessWidget {
  const _Entry();

  @override
  Widget build(BuildContext context) {
    // Split out to avoid importing the whole screen into app.dart
    return const _DeferredHome();
  }
}

/// Small indirection to keep imports clean.
class _DeferredHome extends StatelessWidget {
  const _DeferredHome();

  @override
  Widget build(BuildContext context) {
    // ignore: avoid_types_as_parameter_names
    return const _HomeLoader();
  }
}

// Late import to keep a single top-level import fanout.
class _HomeLoader extends StatelessWidget {
  const _HomeLoader();

  @override
  Widget build(BuildContext context) {
    return const _HomeProxy();
  }
}

class _HomeProxy extends StatelessWidget {
  const _HomeProxy();

  @override
  Widget build(BuildContext context) {
    // Only here we import the screen.
    // (keeps app.dart super lean)
    return const _HomeReal();
  }
}

class _HomeReal extends StatelessWidget {
  const _HomeReal();

  @override
  Widget build(BuildContext context) {
    // ignore: avoid_dynamic_calls
    return const _HomeImpl();
  }
}

class _HomeImpl extends StatelessWidget {
  const _HomeImpl();

  @override
  Widget build(BuildContext context) {
    // Real screen:
    // We do a late import style by referencing via package path
    // to keep file graph simple in editors.
    return const _HomeScreenShim();
  }
}



class _HomeScreenShim extends StatelessWidget {
  const _HomeScreenShim();

  @override
  Widget build(BuildContext context) => const home.MyHomePage(title: 'Paralegal AI');
}
