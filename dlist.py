import os
import re

print("\n" \
      "Instructions\n" \
      "------------\n" \
      "Drive Name -> Choose a name for the drive\n" \
      "Drive ID   -> ID of the drive (Use 'root' for main drive)\n" \
      "Index URL  -> Index link for the drive (Optional)")
msg = ''
if os.path.exists('drive_list'):
    with open('drive_list', 'r+') as f:
        lines = f.read()
    if not re.match(r'^\s*$', lines):
        print("\nList of Drives" \
              "\n--------------")
        print(lines)
        while 1:
            choice = input("Do you want to keep the above list? [Y/n] ")
            if choice == 'y' or choice == 'Y':
                msg = f'{lines}'
                break
            elif choice == 'n' or choice == 'N':
                break
            else:
                print("ERROR: Wrong input")
num = int(input("\nTotal number of drives : "))
count = 1
while count <= num:
    print(f"\nDRIVE - {count}\n" \
          f"----------")
    name = input("Drive Name : ")
    id = input("Drive ID   : ")
    index = input("Index URL  : ")
    if not name or not id:
        print("\nERROR: Drive Name and/or Drive ID empty")
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
print("\nSuccess")
