# Patak

**A federated game platform, basically Roblox but for indie games.**

The main gist:
- Users can create accounts that have coins, XP, level etc.
- Game developers then can register their games on the platform, and get an API key. They can then use the API key in their games to connect the game to the Patak network:
- Users then can log in to Patak in the game, and the coins or XP they get ingame is their coin and XP on their account!


This links all games together into one web where every game shares this account system :)

# Screenshots

<img width="550" height="auto" alt="Képernyőkép 2025-10-04 183203" src="https://github.com/user-attachments/assets/5f67e2ea-2f72-4f89-8ca5-ad885d5333b5" />

<img width="550" height="auto" alt="Képernyőkép 2025-10-04 223419" src="https://github.com/user-attachments/assets/2eb264ce-7465-4fe7-aa71-0c993595f5f7" />

<img width="550" height="auto" alt="Képernyőkép 2025-10-05 204255" src="https://github.com/user-attachments/assets/c913595d-becd-4b62-af48-959bc4c1bbe5" />

<img width="550" height="auto" alt="Képernyőkép 2025-10-05 204403" src="https://github.com/user-attachments/assets/1d50fcd0-6a86-43d8-9720-f2ee853dc3ac" />


# How to use
The site is available [here](http://89.168.88.97:5000/) (sorry too broke for a custom domain for this)

Clientside library available soon!

# How to self-host
1. Download and unzip the latest version.
2. Create a virtual environment and install the dependencies from `requirements.txt`.
3. Run `flask --app patak init-db`.
4. Run `flask --app patak run`: The app should start on localhost:5000!
