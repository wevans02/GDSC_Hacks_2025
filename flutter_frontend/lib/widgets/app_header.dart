// widgets/app_header.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'about_page.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/services.dart';


class AppHeader extends StatelessWidget {
  final String selectedCity;
  final List<String> availableCities;
  final ValueChanged<String> onCityChanged;
  final bool isInChatView;
  final VoidCallback? onLogoTap;

  const AppHeader({
    super.key,
    required this.selectedCity,
    required this.availableCities,
    required this.onCityChanged,
    required this.onLogoTap,
    this.isInChatView = false,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 15.0),
        decoration: BoxDecoration(
          color: Colors.transparent,
          border: Border(
            bottom: BorderSide(
              color: Colors.white.withOpacity(0.2), 
              width: 1
            ),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Left: App Name/Logo
            Row(
              children: [
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: onLogoTap ?? () => Navigator.of(context).popUntil((route) => route.isFirst),
                    child: Text(
                      'Paralegal',
                      style: GoogleFonts.exo2(
                        fontSize: isInChatView ? 28 : 32,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ),
                ),

                const SizedBox(width: 32),

                // About
                // MouseRegion(
                //   cursor: SystemMouseCursors.click,
                //   child: GestureDetector(
                //     onTap: () {
                //       Navigator.of(context).push(
                //         MaterialPageRoute(builder: (_) => const AboutPage()),
                //       );
                //     },
                //     child: Text(
                //       "About",
                //       style: GoogleFonts.poppins(
                //         color: Colors.white,
                //         fontSize: 18,
                //       ),
                //     ),
                //   ),
                // ),

                //const SizedBox(width: 32),

                // Request a City
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () => _showRequestCityDialog(context),
                    child: Text(
                      "Request A City",
                      style: GoogleFonts.poppins(
                        color: Colors.white,
                        fontSize: 18,
                      ),
                    ),
                  ),
                ),

                const SizedBox(width: 32),

                // Feedback
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () => _showFeedbackDialog(context),
                    child: Text(
                      "Feedback",
                      style: GoogleFonts.poppins(color: Colors.white, fontSize: 18),
                    ),
                  ),
                ),
              ],
            ),

            
            //Text("FAQ")
          
            
            // Right: Navigation Menu
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                // City Dropdown
                _buildCityDropdown(context),
                //const SizedBox(width: 16),
                
                // About Button
                //_buildAboutButton(context),
                
                // Optional: Settings button for future features
                const SizedBox(width: 8),
               // _buildSettingsButton(context),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showRequestCityDialog(BuildContext context) {
    final cityController = TextEditingController();
    final emailController = TextEditingController();
    final notesController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) {
        return Dialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 24), // less margin around dialog
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 500), // wider than default
            child: _RequestCityForm(), // we'll build this widget below
          ),
        );
      },
    );

  }


  Widget _buildCityDropdown(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: Colors.white.withOpacity(0.2),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.location_on_outlined,
            size: 16,
            color: Colors.white.withOpacity(0.8),
          ),
          const SizedBox(width: 6),
          DropdownButton<String>(
            value: selectedCity,
            items: availableCities.map((String city) {
              return DropdownMenuItem<String>(
                value: city,
                child: Text(
                  city,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              );
            }).toList(),
            onChanged: (String? newValue) {
              if (newValue != null && newValue != selectedCity) {
                onCityChanged(newValue);
              }
            },
            underline: Container(), // Remove default underline
            dropdownColor: Colors.blueGrey[800],
            icon: Icon(
              Icons.arrow_drop_down,
              color: Colors.white.withOpacity(0.8),
              size: 20,
            ),
            style: TextStyle(
              color: Colors.white,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAboutButton(BuildContext context) {
    return TextButton(
      onPressed: () => Navigator.of(context).pushNamed('/about'),
      style: TextButton.styleFrom(
        foregroundColor: Colors.white.withOpacity(0.8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.info_outline, size: 16),
          const SizedBox(width: 6),
          Text(
            'About',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  void _showFeedbackDialog(BuildContext context) {
    final feedbackController = TextEditingController();
    final emailController = TextEditingController();
    bool submitted = false;

    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            if (submitted) {
              return Dialog(
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(24)),
                insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 500),
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.check_circle, color: Colors.cyan, size: 64),
                        const SizedBox(height: 16),
                        const Text(
                          "Thanks for your feedback!",
                          style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          "We appreciate your input and will use it to improve the experience.",
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 24),
                        ElevatedButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text("Close"),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }

            return Dialog(
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16)),
              insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 500),
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        "Submit Feedback",
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: feedbackController,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: "Your feedback",
                          border: OutlineInputBorder(),
                        ),
                        inputFormatters: [
                          LengthLimitingTextInputFormatter(200), // max 50 chars
                        ],
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: emailController,
                        decoration: const InputDecoration(
                          labelText: "Email (optional)",
                          border: OutlineInputBorder(),
                        ),
                        inputFormatters: [
                          LengthLimitingTextInputFormatter(50), // max 50 chars
                        ],
                      ),
                      const SizedBox(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          TextButton(
                            onPressed: () => Navigator.of(context).pop(),
                            child: const Text("Cancel"),
                          ),
                          ElevatedButton(
                            onPressed: () async {
                              final feedback = feedbackController.text.trim();
                              final email = emailController.text.trim();

                              if (feedback.isEmpty) {
                                return;
                              }

                              try {
                                final response = await http.post(
                                  Uri.parse("https://paralegalbylaw.org/api/feedback"), // change if needed
                                  headers: {"Content-Type": "application/json"},
                                  body: jsonEncode({
                                    "feedback": feedback,
                                    "email": email.isNotEmpty ? email : null,
                                  }),
                                );

                                if (response.statusCode == 200) {
                                  // Success
                                  setState(() => submitted = true);
                                } else {
                                  // Server error
                                  //print("❌ Feedback submit failed: ${response.body}");
                                  showDialog(
                                    context: context,
                                    builder: (_) => const AlertDialog(
                                      title: Text("Error"),
                                      content: Text("Something went wrong submitting feedback."),
                                    ),
                                  );
                                }
                              } catch (e) {
                                // Network error
                                //print("❌ Network error: $e");
                                showDialog(
                                  context: context,
                                  builder: (_) => const AlertDialog(
                                    title: Text("Error"),
                                    content: Text("Could not connect to server."),
                                  ),
                                );
                              }
                            },
                            child: const Text("Submit"),
                          ),

                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }


  Widget _buildSettingsButton(BuildContext context) {
    return IconButton(
      onPressed: () {
        // Future: Settings dialog
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Settings coming soon!'),
            backgroundColor: Colors.blue.shade600,
            duration: Duration(seconds: 2),
          ),
        );
      },
      icon: Icon(
        Icons.settings_outlined,
        color: Colors.white.withOpacity(0.6),
        size: 20,
      ),
      tooltip: 'Settings (Coming Soon)',
      style: IconButton.styleFrom(
        padding: EdgeInsets.all(8),
      ),
    );
  }

  // void _showAboutDialog(BuildContext context) {
  //   showDialog(
  //     context: context,
  //     builder: (context) => const AboutAppDialog(),
  //   );
  // }
}

class _RequestCityForm extends StatefulWidget {
  @override
  State<_RequestCityForm> createState() => _RequestCityFormState();
}

class _RequestCityFormState extends State<_RequestCityForm> {
  final cityController = TextEditingController();
  final emailController = TextEditingController();
  final notesController = TextEditingController();

  bool submitted = false;

  @override
  Widget build(BuildContext context) {
    if (submitted) {
      // Confirmation screen
      return Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle, color: Colors.cyan, size: 64),
            const SizedBox(height: 16),
            const Text(
              "Thanks for your input!",
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            const Text(
              "The city has been added to our list.\nIt may take some time, but we'll email you once it's available.",
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text("Close"),
            )
          ],
        ),
      );
    }

    // Input form
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: cityController,
            decoration: const InputDecoration(labelText: "City name *", border: OutlineInputBorder(),),
            
            inputFormatters: [
              LengthLimitingTextInputFormatter(50), // max 50 chars
            ],
          ),
          const SizedBox(height: 6),
          Text(
            "We'll add the bylaws for this city when we can",
            style: TextStyle(color: Colors.white.withAlpha(188))
          ),


          const SizedBox(height: 16),

          TextField(
            controller: emailController,
            decoration: const InputDecoration(labelText: "Email (optional)", border: OutlineInputBorder(),),
            inputFormatters: [
              LengthLimitingTextInputFormatter(50), // max 50 chars
            ],
          ),
          const SizedBox(height: 6),
          Text("If you want to be notified when it's added", style: TextStyle(color: Colors.white.withAlpha(188))),

          const SizedBox(height: 16),

          TextField(
            controller: notesController,
            maxLines: 3,
            decoration: const InputDecoration(labelText: "Description / Notes", border: OutlineInputBorder()),
            inputFormatters: [
              LengthLimitingTextInputFormatter(200), // max 50 chars
            ],
          ),
          const SizedBox(height: 6),
          Text("Any other comments you'd like to add", style: TextStyle(color: Colors.white.withAlpha(188))),

          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text("Cancel"),
              ),
              ElevatedButton(
                onPressed: () async {
                  final city = cityController.text.trim();
                  final email = emailController.text.trim();
                  final notes = notesController.text.trim();

                  if (city.isEmpty) {
                    showDialog(
                      context: context,
                      builder: (_) => const AlertDialog(
                        title: Text("Missing city name"),
                        content: Text("Please enter a city."),
                      ),
                    );
                    return;
                  }

                  try {
                    final response = await http.post(
                      Uri.parse("https://paralegalbylaw.org/api/request-city"), // or your LAN IP in dev
                      headers: {"Content-Type": "application/json"},
                      body: jsonEncode({
                        "city": city,
                        "email": email.isNotEmpty ? email : null,
                        "notes": notes.isNotEmpty ? notes : null,
                      }),
                    );

                    if (response.statusCode == 200) {
                      setState(() => submitted = true); // show thank-you screen
                    } else {
                      //print("❌ Request city failed: ${response.body}");
                      showDialog(
                        context: context,
                        builder: (_) => const AlertDialog(
                          title: Text("Error"),
                          content: Text("Something went wrong submitting your request."),
                        ),
                      );
                    }
                  } catch (e) {
                    //print("❌ Network error: $e");
                    showDialog(
                      context: context,
                      builder: (_) => const AlertDialog(
                        title: Text("Error"),
                        content: Text("Could not connect to the server."),
                      ),
                    );
                  }
                },
                child: const Text("Submit"),
              ),

            ],
          ),
        ],
      ),
    );
  }

  
}
