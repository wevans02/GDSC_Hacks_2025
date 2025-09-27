import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// Helper function for the main text style to avoid repetition
TextStyle _titleTextStyle() {
  return GoogleFonts.poppins(
    fontSize: 48,
    fontWeight: FontWeight.w700,
    // Note: The color here is only for text not covered by the gradient/ShaderMask
    color: Colors.white, 
  );
}

class TitleText extends StatelessWidget {
  const TitleText({super.key});

  @override
  Widget build(BuildContext context) {
    // Define the gradient
    const LinearGradient bylawGradient = LinearGradient(
      colors: <Color>[Colors.cyan, Colors.cyanAccent],
      // Optional: Define start/end alignment for more control
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );

    // The text with the gradient applied will be "Bylaw"
    final Widget bylawText = ShaderMask(
      // The ShaderMask applies the gradient to its child using the gradient's 
      // createShader method, which automatically uses the bounds of the child widget.
      shaderCallback: (Rect bounds) {
        return bylawGradient.createShader(bounds);
      },
      child: Text(
        'Bylaw',
        style: _titleTextStyle().copyWith(
          // Text color must be a non-transparent color (e.g., white)
          // so the gradient is visible through it.
          color: Colors.white, 
        ),
      ),
    );

    // We use a Row to lay out the text components to easily separate the part 
    // that needs the gradient (bylawText) from the rest.
    return Center(
      child: Wrap( // Use Wrap to allow the text to wrap like RichText does
        alignment: WrapAlignment.center,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: <Widget>[
          Text(
            'AI Powered Municipal ',
            style: _titleTextStyle(),
          ),
          // The ShaderMasked text widget
          bylawText,
          Text(
            ' Search',
            style: _titleTextStyle(),
          ),
        ],
      ),
    );
  }
}