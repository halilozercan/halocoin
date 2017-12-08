export const timestampToDatetime = (timestamp) => {
    var date = new Date(timestamp*1000);
    var formattedTime = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    return formattedTime;
}