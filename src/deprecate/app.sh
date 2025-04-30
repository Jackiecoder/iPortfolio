if [ "$1" == "-d" ]; then
    python3 ./src/app.py -d
elif [ "$1" == "--ytd" ]; then
    python3 ./src/app.py --ytd
else
    echo "Invalid argument. Please use '-d' or '--ytd'."
fi