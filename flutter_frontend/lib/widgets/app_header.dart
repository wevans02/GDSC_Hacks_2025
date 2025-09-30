// widgets/app_header.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
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
    final screenWidth = MediaQuery.of(context).size.width;
    const cutoff = 700.0; // adjust breakpoint as needed
    final isNarrow = screenWidth < cutoff;

    return SafeArea(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 15.0),
        decoration: BoxDecoration(
          color: Colors.transparent,
          border: Border(
            bottom: BorderSide(
              color: Colors.white.withOpacity(0.2),
              width: 1,
            ),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Left: App Name/Logo
            MouseRegion(
              cursor: SystemMouseCursors.click,
              child: GestureDetector(
                onTap: onLogoTap ??
                    () => Navigator.of(context).popUntil((route) => route.isFirst),
                child: Text(
                  'Paralegal',
                  style: GoogleFonts.exo2(
                    fontSize: isInChatView ? 24 : 28,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                    letterSpacing: 1.2,
                  ),
                ),
              ),
            ),

            // Right: City dropdown + nav items (or hamburger)
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildCityDropdown(context),
                const SizedBox(width: 12),
                if (!isNarrow) ...[
                  MouseRegion(
                    cursor: SystemMouseCursors.click,
                    child: _buildNavLink(
                      "Request A City",
                      () => _showRequestCityDialog(context),
                    ),
                  ),
                  const SizedBox(width: 20),
                  MouseRegion(
                    cursor: SystemMouseCursors.click,
                    child: _buildNavLink(
                      "Feedback",
                      () => _showFeedbackDialog(context),
                    ),
                  ),
                ] else
                  _buildHamburgerMenu(context),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Hamburger menu for narrow screens
  Widget _buildHamburgerMenu(BuildContext context) {
    return PopupMenuButton<int>(
      icon: Icon(Icons.menu, color: Colors.white),
      onSelected: (value) {
        if (value == 1) _showRequestCityDialog(context);
        if (value == 2) _showFeedbackDialog(context);
      },
      itemBuilder: (context) => [
        PopupMenuItem(value: 1, child: Text("Request A City")),
        PopupMenuItem(value: 2, child: Text("Feedback")),
      ],
    );
  }

  Widget _buildNavLink(String label, VoidCallback onTap) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onTap,
        child: Text(
          label,
          style: GoogleFonts.poppins(color: Colors.white, fontSize: 16),
        ),
      ),
    );
  }

  void _showRequestCityDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) {
        return Dialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          insetPadding:
              const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 500),
            child: _RequestCityForm(),
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
            
            //focusColor: Colors.white,
            value: selectedCity,
            items: availableCities.map((String city) {
              return DropdownMenuItem<String>(
                value: city,
                child: Text(
                  city,
                  style: const TextStyle(
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
            underline: Container(),
            dropdownColor: Colors.grey[900]!,
            icon: Icon(
              Icons.arrow_drop_down,
              color: Colors.white.withOpacity(0.8),
              size: 20,
            ),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
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
    bool isSubmitting = false; // NEW


    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            if (submitted) {
              return Dialog(
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(24)),
                insetPadding:
                    const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 500),
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.check_circle,
                            color: Colors.cyan, size: 64),
                        const SizedBox(height: 16),
                        const Text(
                          "Thanks for your feedback!",
                          style: TextStyle(
                              fontSize: 22, fontWeight: FontWeight.bold),
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
              insetPadding:
                  const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 500),
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        "Submit Feedback",
                        style: TextStyle(
                            fontSize: 20, fontWeight: FontWeight.bold),
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
                          LengthLimitingTextInputFormatter(200),
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
                          LengthLimitingTextInputFormatter(50),
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
                            onPressed: isSubmitting
                                ? null // disable during submit
                                : () async {
                                    final feedback = feedbackController.text.trim();
                                    final email = emailController.text.trim();

                                    if (feedback.isEmpty) return;

                                    setState(() => isSubmitting = true);

                                    try {
                                      final response = await http.post(
                                        Uri.parse("https://api.paralegalbylaw.org/api/feedback"),
                                        headers: {"Content-Type": "application/json"},
                                        body: jsonEncode({
                                          "feedback": feedback,
                                          "email": email.isNotEmpty ? email : null,
                                        }),
                                      );

                                      if (response.statusCode == 200) {
                                        setState(() {
                                          submitted = true;
                                          isSubmitting = false;
                                        });
                                      } else {
                                        setState(() => isSubmitting = false);
                                        _showError(context, "Something went wrong submitting feedback.");
                                      }
                                    } catch (e) {
                                      setState(() => isSubmitting = false);
                                      _showError(context, "Could not connect to server.");
                                    }
                                  },
                            child: isSubmitting
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                    ),
                                  )
                                : const Text("Submit"),
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
  bool isSubmitting = false;

  @override
  Widget build(BuildContext context) {
    if (submitted) {
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

    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: cityController,
            decoration: const InputDecoration(
                labelText: "City name *", border: OutlineInputBorder()),
            inputFormatters: [LengthLimitingTextInputFormatter(50)],
          ),
          const SizedBox(height: 6),
          Text("We'll add the bylaws for this city when we can",
              style: TextStyle(color: Colors.white.withAlpha(188))),
          const SizedBox(height: 16),
          TextField(
            controller: emailController,
            decoration: const InputDecoration(
                labelText: "Email (optional)", border: OutlineInputBorder()),
            inputFormatters: [LengthLimitingTextInputFormatter(50)],
          ),
          const SizedBox(height: 6),
          Text("If you want to be notified when it's added",
              style: TextStyle(color: Colors.white.withAlpha(188))),
          const SizedBox(height: 16),
          TextField(
            controller: notesController,
            maxLines: 3,
            decoration: const InputDecoration(
                labelText: "Description / Notes",
                border: OutlineInputBorder()),
            inputFormatters: [LengthLimitingTextInputFormatter(200)],
          ),
          const SizedBox(height: 6),
          Text("Any other comments you'd like to add",
              style: TextStyle(color: Colors.white.withAlpha(188))),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text("Cancel"),
              ),
              ElevatedButton(
                onPressed: isSubmitting
                    ? null
                    : () async {
                        final city = cityController.text.trim();
                        final email = emailController.text.trim();
                        final notes = notesController.text.trim();

                        if (city.isEmpty) {
                          _showError(context, "Please enter a city.");
                          return;
                        }

                        setState(() => isSubmitting = true);

                        try {
                          final response = await http.post(
                            Uri.parse("https://api.paralegalbylaw.org/api/request-city"),
                            headers: {"Content-Type": "application/json"},
                            body: jsonEncode({
                              "city": city,
                              "email": email.isNotEmpty ? email : null,
                              "notes": notes.isNotEmpty ? notes : null,
                            }),
                          );

                          if (response.statusCode == 200) {
                            setState(() {
                              submitted = true;
                              isSubmitting = false;
                            });
                          } else {
                            setState(() => isSubmitting = false);
                            _showError(context, "Something went wrong submitting your request.");
                          }
                        } catch (e) {
                          setState(() => isSubmitting = false);
                          _showError(context, "Could not connect to the server.");
                        }
                      },
                child: isSubmitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : const Text("Submit"),
              ),

            ],
          ),
        ],
      ),
    );
  }
}

 void _showError(BuildContext context, String msg) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Error"),
        content: Text(msg),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text("OK"),
          ),
        ],
      ),
    );
  }
