import React, { Component } from 'react';
import {Card, CardHeader} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import FontIcon from 'material-ui/FontIcon';
import {green500} from 'material-ui/styles/colors';

class Balance extends Component {

  render() {
    let balance = 0;
    if(this.props.account !== null){
      balance = this.props.account.amount;
    }
    return (
      <Card>
        <CardHeader
          title="Balance"
          subtitle={balance}
          avatar={<Avatar backgroundColor={green500} icon={<FontIcon className="material-icons">trending_up</FontIcon>} />}
        />
      </Card>
      
    );
  }
}

export default Balance;