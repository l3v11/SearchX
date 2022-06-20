import json
import os
import subprocess
import time

print("\nGenerate a file from the below list")
print("\n\tA. drive_list")
print("\tB. dest_list")

choice = input("\nChoose either A or B > ")

if choice in ['A', 'a', '1']:
    print("\nGenerate the drive_list file with the below methods")
    print("\n\tA. All Drives (automatic)")
    print("\tB. Selected Drives (manual)")

    choice = input("\nChoose either A or B > ")

    if choice in ['A', 'a', '1']:
        input("\nNOTICE: Make sure Rclone is installed on your system PATH variable and Google Drive remote is configured properly\n\nPress ENTER to continue")

        print("\nList of remotes")
        print("---------------")
        subprocess.run(['rclone', 'listremotes', '--long'])

        remote = input("\nEnter a drive remote > ")

        print("\nProcessing all drives")

        with open('drives.txt', 'w') as drives:
            subprocess.run(['rclone', 'backend', 'drives', f'{remote}'], stdout=drives)

        msg = ''
        with open('drives.txt', 'r+', encoding='utf8') as f1:
            lines = json.loads(f1.read())
            for count, item in enumerate(lines, 1):
                id = item['id']
                name = item['name'].strip().replace(' ', '_')
                msg += f'{name} {id}\n'
        time.sleep(2)

        with open('drive_list', 'w', encoding='utf8') as f2:
            f2.truncate(0)
            f2.write(msg)
        time.sleep(2)

        os.remove('drives.txt')
        print(f"\nGenerated the drive_list file with {len(lines)} drives")
        exit()

    elif choice in ['B', 'b', '2']:
        print("\nInstructions" \
              "\n------------" \
              "\nDrive Name > Name of the drive" \
              "\nDrive ID   > ID of the drive" \
              "\nIndex URL  > Index link for the drive (Optional)")

        num = int(input("\nTotal number of drives > "))
        msg = ''
        for count in range(1, num + 1):
            print(f"\nDRIVE - {count}\n" \
                  f"----------")
            name = input("Drive Name > ")
            if not name:
                print("\nERROR: Drive Name cannot be empty")
                exit(1)
            name = name.replace(" ", "_")
            id = input("Drive ID   > ")
            if not id:
                print("\nERROR: Drive ID cannot be empty")
                exit(1)
            index = input("Index URL  > ")
            if index:
                if index[-1] == "/":
                    index = index[:-1]
            else:
                index = ''
            msg += f"{name} {id} {index}\n"

        with open('drive_list', 'w') as f:
            f.truncate(0)
            f.write(msg)

        print(f"\nGenerated the drive_list file with {num} drives")
        exit()

    else:
        print("\nERROR: Wrong input")
        exit(1)

elif choice in ['B', 'b', '2']:
    print("\nInstructions" \
          "\n------------" \
          "\nDrive Key  > A random short name for the drive" \
          "\nDrive ID   > ID of the drive" \
          "\nIndex URL  > Index link for the drive (Optional)")

    num = int(input("\nTotal number of drives > "))
    msg = ''
    for count in range(1, num + 1):
        print(f"\nDRIVE - {count}\n" \
              f"----------")
        key = input("Drive Key  > ")
        if not key:
            print("\nERROR: Drive Key cannot be empty")
            exit(1)
        key = key.replace(" ", "_")
        id = input("Drive ID   > ")
        if not id:
            print("\nERROR: Drive ID cannot be empty")
            exit(1)
        index = input("Index URL  > ")
        if index:
            if index[-1] == "/":
                index = index[:-1]
        else:
            index = ''
        msg += f"{key} {id} {index}\n"

    with open('dest_list', 'w') as f:
        f.truncate(0)
        f.write(msg)

    print(f"\nGenerated the dest_list file with {num} drives")
    exit()

else:
    print("\nERROR: Wrong input")
    exit(1)
