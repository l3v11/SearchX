import json
import os
import subprocess
import time

print("\nGenerate the \033[1;96mdrive_list\033[m file with the below methods")
print("\n\t\033[1;95mA.\033[m All Drives (automatic)")
print("\t\033[1;95mB.\033[m Selected Drives (manual)")

choice = input("\nChoose either \033[1;95mA\033[m or \033[1;95mB\033[m > ")

if choice == 'A' or choice == 'a' or choice == '1':
    input("\n\033[1;95mNOTICE:\033[m Make sure Rclone is installed on your system PATH variable and Google Drive remote is configured properly\n\nPress ENTER to continue")

    print("\n\033[1;93mList of remotes")
    print("---------------\033[m")
    subprocess.run(['rclone', 'listremotes', '--long'])

    remote = input("\n\033[1;94mEnter a drive remote >\033[m ")

    print("\nProcessing all drives")

    with open('drives.txt', 'w') as drives:
        subprocess.run(['rclone', 'backend', 'drives', f'{remote}'], stdout=drives)

    msg = ''
    with open('drives.txt', 'r+') as f1:
        lines = json.loads(f1.read())
        for count, item in enumerate(lines, 1):
            id = item['id']
            name = item['name'].strip().replace(' ', '_')
            msg += f'{name} {id}\n'
    time.sleep(2)

    with open('drive_list', 'w') as f2:
        f2.truncate(0)
        f2.write(msg)
    time.sleep(2)

    os.remove('drives.txt')
    print(f"\nGenerated \033[1;96mdrive_list\033[m file with \033[1;96m{len(lines)}\033[m drives")
    exit()

if choice == 'B' or choice == 'b' or choice == '2':
    num = int(input("\n\033[1;94mTotal number of drives >\033[m "))
    count = 1
    msg = ''
    while count <= num:
        print(f"\n\033[1;93mDRIVE - {count}\n" \
              f"----------\033[m")
        name = input("Drive Name > ")
        id = input("Drive ID   > ")
        index = input("Index URL  > ")
        if not name or not id:
            print("\n\033[1;91mERROR:\033[m Drive Name and/or Drive ID is empty")
            exit(1)
        name = name.replace(" ", "_")
        if index:
            if index[-1] == "/":
                index = index[:-1]
        else:
            index = ''
        count += 1
        msg += f"{name} {id} {index}\n"

    with open('drive_list', 'w') as f:
        f.truncate(0)
        f.write(msg)

    print(f"\nGenerated \033[1;96mdrive_list\033[m file with \033[1;96m{num}\033[m drives")
    exit()

else:
    print("\n\033[1;91mERROR:\033[m Wrong input")
    exit(1)
