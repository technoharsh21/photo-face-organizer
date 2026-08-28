export interface FAQItem {
  id: string;
  category: 'General' | 'Privacy & Safety' | 'Features' | 'Installation & Hardware';
  question: string;
  answer: string;
}

export const FAQ_DATA: FAQItem[] = [
  {
    id: "cloud-privacy",
    category: "Privacy & Safety",
    question: "Does Photo Face Organizer upload my photos to any server?",
    answer: "No, never. Photo Face Organizer is 100% local-first software. All face detection, face recognition encoding, profile storage, and photo routing happen entirely on your computer's local CPU/GPU. No internet connection is required for photo scanning."
  },
  {
    id: "original-files",
    category: "Privacy & Safety",
    question: "What happens to my original photos during a scan?",
    answer: "Your original photos are never moved, deleted, renamed, or modified. Photo Face Organizer operates strictly in copy mode: it reads your source photos and creates clean copies inside your designated target output directory."
  },
  {
    id: "group-photos",
    category: "Features",
    question: "Does it support group photos with multiple people?",
    answer: "Yes! If a photo contains multiple recognized faces (e.g. Alice AND Bob), the application copies that photo into Alice's folder, Bob's folder, and any Group Profile folder that requires both Alice and Bob together."
  },
  {
    id: "group-profile-rules",
    category: "Features",
    question: "How do Group Profiles (e.g. 'Family' or 'Me & Friend') work?",
    answer: "Group Profiles enforce compulsory multi-person matching. A photo is ONLY copied into a Group Profile folder if ALL compulsory individuals defined for that profile are detected together in that single photo."
  },
  {
    id: "no-match",
    category: "Features",
    question: "What happens to photos where no matching person is found?",
    answer: "Photos that contain unrecognized faces or no matching profiles are copied safely into a dedicated 'No Match' folder inside your output directory. Unmatched face thumbnails are also stored in the 'Unknown Faces' tab in the app so you can review them or turn them into new profiles."
  },
  {
    id: "multiple-references",
    category: "Features",
    question: "Can I add multiple reference photos for a single person?",
    answer: "Yes! You can add multiple reference photos of the same person from different angles, lighting conditions, or ages to improve recognition accuracy."
  },
  {
    id: "gpu-support",
    category: "Installation & Hardware",
    question: "Does Photo Face Organizer require a dedicated GPU?",
    answer: "No, a dedicated GPU is not required. Photo Face Organizer runs efficiently on standard multi-core CPUs. If a compatible NVIDIA CUDA GPU is available on your machine, the engine can utilize GPU acceleration for faster batch scanning."
  },
  {
    id: "supported-os",
    category: "Installation & Hardware",
    question: "Which operating systems are supported?",
    answer: "Photo Face Organizer supports 64-bit Linux (Ubuntu, Debian, Mint, Fedora), Windows (10/11 64-bit), and macOS (Apple Silicon & Intel)."
  },
  {
    id: "multiple-folders",
    category: "General",
    question: "Can I scan multiple folders or entire hard drives at once?",
    answer: "Yes, you can select multiple source folders and enable recursive scanning to analyze all subdirectories automatically in a single scan run."
  },
  {
    id: "app-data-location",
    category: "General",
    question: "Where is my profile and scan history data stored?",
    answer: "All profiles, face encodings, and scan history are saved in standard OS application data locations (e.g., ~/.local/share/PhotoFaceOrganizer on Linux, %APPDATA%/PhotoFaceOrganizer on Windows). No data ever leaves your computer."
  },
  {
    id: "updating",
    category: "Installation & Hardware",
    question: "How do I update the application?",
    answer: "On Linux, download and install the latest .deb package or run 'pip install --upgrade git+https://github.com/technoharsh21/photo-face-organizer.git'. On Windows, download the latest setup installer from our Releases page."
  },
  {
    id: "uninstalling",
    category: "General",
    question: "How do I uninstall Photo Face Organizer?",
    answer: "On Linux, run 'sudo dpkg -r photo-face-organizer' or 'pipx uninstall photo-face-organizer'. On Windows, use 'Add or Remove Programs' in Control Panel."
  }
];
